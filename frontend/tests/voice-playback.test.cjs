// Execute the real component playback functions with a small Web Audio mock.
// No browser test runner dependency is required for these async race regressions.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function loadPlayback(file, stopName) {
  const text = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
  const tree = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const functions = [];
  function visit(node) {
    if (ts.isFunctionDeclaration(node) && ['playPcmChunk', stopName].includes(node.name?.text)) {
      functions.push(node.getText(tree));
    } else if (ts.isVariableDeclaration(node) && ['playPcmChunk', stopName].includes(node.name.getText(tree))) {
      functions.push(`const ${node.getText(tree)};`);
    }
    ts.forEachChild(node, visit);
  }
  visit(tree);
  assert.equal(functions.length, 2);
  const sources = [];
  const context = {
    currentTime: 0, state: 'running', destination: {},
    createBuffer: (_, length) => ({ duration: length / 16000, getChannelData: () => new Float32Array(length) }),
    createBufferSource: () => {
      const source = { connect() {}, start() {}, stop() {}, onended: null };
      sources.push(source);
      return source;
    },
    createGain: () => ({ gain: { value: 1, setValueAtTime() {} }, connect() {} }),
  };
  const scope = {
    ArrayBuffer, Blob, DataView, Int16Array, console,
    audioCtxRef: { current: context }, playbackEpochRef: { current: 0 },
    audioSourcesRef: { current: [] }, nextPlayTimeRef: { current: 0 },
    masterGainRef: { current: null }, isAgentSpeakingRef: { current: false },
    hangupTimeoutRef: { current: null },
    setIsSpeaking() {}, setIsListening() {}, setCallStatus() {},
  };
  const code = ts.transpileModule(functions.join('\n'), { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText;
  vm.runInNewContext(`${code}\nthis.play = playPcmChunk; this.stop = ${stopName};`, scope);
  return { scope, context, sources };
}

function packet() {
  const data = new ArrayBuffer(12);
  new DataView(data).setUint32(0, 16000, true);
  return data;
}

for (const [file, stopName] of [
  ['app/(dashboard)/agents/[id]/page.tsx', 'stopPlayback'],
  ['components/test-agent/TestAgentModal.tsx', 'stopAudioPlayback'],
]) {
  test(`${file}: interrupt stops queued playback without stale ended callbacks`, async () => {
    const { scope, sources } = loadPlayback(file, stopName);
    await scope.play(packet());
    assert.equal(sources.length, 1);
    assert.equal(typeof sources[0].onended, 'function');
    scope.stop();
    assert.equal(sources[0].onended, null);
    assert.equal(scope.audioSourcesRef.current.length, 0);
    assert.equal(scope.nextPlayTimeRef.current, 0);
  });

  test(`${file}: interrupt while AudioContext resumes cannot restart old speech`, async () => {
    const { scope, context, sources } = loadPlayback(file, stopName);
    let resume;
    context.state = 'suspended';
    context.resume = () => new Promise((resolve) => { resume = resolve; });
    const pending = scope.play(packet());
    scope.stop();
    context.state = 'running';
    resume();
    await pending;
    assert.equal(sources.length, 0);
    await scope.play(packet());
    assert.equal(sources.length, 1, 'new speech must still play after interruption');
  });

  test(`${file}: interrupt during Blob conversion discards the late chunk`, async () => {
    const { scope, sources } = loadPlayback(file, stopName);
    let resolve;
    const blob = new Blob([packet()]);
    blob.arrayBuffer = () => new Promise((done) => { resolve = done; });
    const pending = scope.play(blob);
    scope.stop();
    resolve(packet());
    await pending;
    assert.equal(sources.length, 0);
  });
}

function loadStudioCallback(name, values) {
  const file = 'app/(dashboard)/agents/[id]/page.tsx';
  const text = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
  const tree = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  let callback;
  const state = {};
  function visit(node) {
    if (ts.isVariableDeclaration(node) && node.name.getText(tree) === name) {
      callback = node.initializer.arguments[0].getText(tree);
    }
    if (ts.isIdentifier(node) && /^set[A-Z]/.test(node.text)) {
      values[node.text] = (value) => { state[node.text] = value; };
    }
    ts.forEachChild(node, visit);
  }
  visit(tree);
  assert.ok(callback);
  const code = ts.transpileModule(`this.callback = ${callback}`, { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText;
  vm.runInNewContext(code, values);
  return { callback: values.callback, state };
}

test('Studio loads zero sensitivity and resets settings when changing versions', async () => {
  let config = { barge_in_sensitivity: 0, speech_speed: 1.2, knowledge_strictness: 'strict', tools: { webhook: true } };
  const { callback, state } = loadStudioCallback('loadAgent', {
    id: 'agent', toast: { error: assert.fail },
    api: {
      agents: {
        get: async () => ({ name: 'Agent' }),
        versions: { list: async () => [{ id: 'draft', status: 'draft', configuration: config }] },
        pipelineStatus: async () => null,
      },
      voiceProfiles: { list: async () => [] },
      knowledge: { list: async () => [], getForAgent: async () => [], getContext: async () => null },
    },
  });
  await callback();
  assert.equal(state.setSensitivity, 0);
  assert.equal(state.setSpeechSpeed, 1.2);
  assert.equal(state.setToolWebhook, true);
  config = {};
  await callback();
  assert.equal(state.setSensitivity, 70);
  assert.equal(state.setSpeechSpeed, 1);
  assert.equal(state.setToolWebhook, false);
  assert.equal(state.setKnowledgeStrictness, 'flexible');
});

test('Studio saves edits without deleting non-editor configuration or unknown tools', () => {
  const { callback } = loadStudioCallback('buildConfigPayload', {
    activeVersion: { configuration: { custom_option: 42, system_prompt: 'old', tools: { custom_tool: true, webhook: true } } },
    agentName: 'Agent', greeting: '', instructions: 'updated', primaryLanguage: 'en-IN',
    inputVariables: {}, outputVariables: [], speechSpeed: 1, sensitivity: 0, voiceId: '',
    knowledgeStrictness: 'flexible', toolWhatsApp: false, toolCalendar: false,
    toolWebhook: false, webhookUrl: '',
  });
  const result = callback();
  assert.equal(result.custom_option, 42);
  assert.equal(result.tools.custom_tool, true);
  assert.equal(result.tools.webhook, false);
  assert.equal(result.system_prompt, 'updated');
  assert.equal(result.barge_in_sensitivity, 0);
});

for (const file of ['app/(dashboard)/agents/[id]/page.tsx', 'components/test-agent/TestAgentModal.tsx']) {
  test(`${file}: quiet speech and trailing silence reach VAD during playback`, () => {
    const text = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
    const tree = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    let callback;
    function visit(node) {
      if (ts.isBinaryExpression(node) && node.left.getText(tree) === 'processor.onaudioprocess') {
        callback = node.right.getText(tree);
      }
      ts.forEachChild(node, visit);
    }
    visit(tree);
    assert.ok(callback);
    const frames = [];
    const ws = { readyState: 1, send: (frame) => frames.push(frame) };
    const scope = {
      ws, wsRef: { current: ws }, WebSocket: { OPEN: 1 },
      initSentRef: { current: true }, micMutedRef: { current: false },
      audioCtx: { currentTime: 0, sampleRate: 16000 }, nextPlayTimeRef: { current: 10 },
      sensitivity: 70, downsampleTo16k: (input) => new Int16Array(input.length),
    };
    const code = ts.transpileModule(`this.capture = ${callback}`, { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText;
    vm.runInNewContext(code, scope);
    scope.capture({ inputBuffer: { getChannelData: () => new Float32Array(512).fill(0.005) } });
    scope.capture({ inputBuffer: { getChannelData: () => new Float32Array(512) } });
    assert.equal(frames.length, 2);
  });
}

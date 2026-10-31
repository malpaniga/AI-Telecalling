# Design: Plivo Phone Number Provider & Multi-Organization Support

## Intent and Context
Administrators purchase DID phone numbers directly from Plivo (plivo.com) and need to add and manage them in the Admin Dashboard **Phone Number Inventory**, identically to how Vobiz numbers are configured using API credentials.

Admins assign these Plivo phone numbers to one or more organizations simultaneously, allowing those organizations to select them as their **Calling Number** when running outbound campaigns or executing live phone tests in the **AI Agent Studio**.

Furthermore, the integration supports customer inbound calls placed to these numbers, routing them to the designated inbound organization's AI agent over real-time WebSockets, while debiting the inbound organization's credit balance.

---

## Goals
1. **Admin Plivo Configuration & Inventory Management**:
   - Provide first-class support for `provider: "plivo"` in the Admin Phone Number Inventory.
   - When adding a Plivo number (`POST /api/v1/phone-numbers/admin`), allow the admin to enter Plivo-specific credentials:
     - `plivo_auth_id` (Plivo Auth ID)
     - `plivo_auth_token` (Plivo Auth Token)
     - (Optional) `plivo_app_id` (Plivo Application / Subaccount ID)
   - Store these credentials securely in `provider_metadata` on the `PhoneNumber` document. Provider details must never be exposed to customer-facing APIs (`_to_customer_view`).

2. **Plivo Telephony Provider Adapter**:
   - Implement `PlivoTelephonyProvider` (`backend/providers/telephony/plivo.py`) inheriting from `TelephonyProvider`.
   - Implement `initiate_call(to, from_number, **kwargs)`:
     - Send `POST https://api.plivo.com/v1/Account/{auth_id}/Call/` with HTTP Basic Authentication `(auth_id, auth_token)`.
     - Payload:
       ```json
       {
         "from": from_number,
         "to": to,
         "answer_url": "{public_base_url}/plivo/voice?call_id={call_id}&agent_id={agent_id}&lang={lang}",
         "answer_method": "POST"
       }
       ```
     - Return `{ "provider_resource_id": request_uuid, "status": "queued" }`.
   - Implement `hangup_call` via `DELETE https://api.plivo.com/v1/Account/{auth_id}/Call/{call_uuid}/`.
   - Implement `get_call_status` via `GET https://api.plivo.com/v1/Account/{auth_id}/Call/{call_uuid}/`.

3. **PlivoXML & Real-Time Media Stream (`/plivo/voice` & `/ws/plivo`)**:
   - `POST /plivo/voice`: Responds with PlivoXML instructing Plivo to connect a bidirectional media stream to our WebSocket:
     ```xml
     <?xml version="1.0" encoding="UTF-8"?>
     <Response>
       <Stream bidirectional="true" keepCallAlive="true" streamTimeout="7200" contentType="audio/x-l16;rate=8000">wss://{public_host}/ws/plivo?call_id={call_id}&amp;agent_id={agent_id}&amp;lang={lang}</Stream>
       <Hangup/>
     </Response>
     ```
   - WebSocket `/ws/plivo`:
     - Implements `PlivoTransport` interfacing with `CallSession`.
     - Inbound frames:
       - `event: "start"`: Captures `streamId`, call metadata.
       - `event: "media"`: Decodes base64 8 kHz mu-law audio, resamples to 16 kHz PCM, feeds into `CallSession` (VAD / STT).
     - Outbound audio:
       - Receives 16 kHz PCM chunks from `CallSession` TTS, converts to 8 kHz mu-law, encodes to base64, and sends:
         ```json
         {
           "event": "playAudio",
           "streamId": streamId,
           "media": {
             "contentType": "audio/x-mulaw",
             "sampleRate": 8000,
             "payload": "<base64_data>"
           }
         }
         ```
     - Barge-in:
       - On interruption, sends `{ "event": "clearAudio", "streamId": streamId }` to immediately flush buffered audio on Plivo.
     - Termination:
       - When WebSocket closes or receives disconnect, gracefully finalizes the `CallSession`.

4. **Inbound Call Handling, CRM Integration & Billing**:
   - If an inbound call hits `/plivo/voice` without a `call_id`:
     - Look up the `PhoneNumber` in DB matching `number == To`.
     - Check `inbound_organization_id` (fallback to the first organization in `assigned_org_ids`).
     - **Credit Authorization**: Check if the organization has positive credits (`CreditService.can_start_call`). If credits <= 0, return PlivoXML prompt:
       ```xml
       <?xml version="1.0" encoding="UTF-8"?>
       <Response>
         <Speak>This number is temporarily unavailable.</Speak>
         <Hangup/>
       </Response>
       ```
     - Reserve initial credits for the inbound call (`CreditService.reserve`).
     - Look up or create a `Lead` record for the caller (`phone == From`, `source="plivo_inbound"`) under `inbound_organization_id`.
     - Find the designated `inbound_agent_id` or the organization's primary active AI Agent.
     - Create an inbound `Call` record with `provider="plivo"`.
     - Return the PlivoXML pointing to `/ws/plivo` with the resolved `call_id`, `agent_id`, and `org_id`.
     - On WebSocket disconnect, finalize the call and settle consumed credits (`CreditService.settle`).

5. **Outbound Dispatch Integration (Campaigns & AI Studio)**:
   - In `CallService.initiate_call`:
     - When `from_number` has `provider == "plivo"`:
       - Resolve credentials `plivo_auth_id` and `plivo_auth_token` from `phone_doc.provider_metadata`.
       - Invoke `PlivoTelephonyProvider.initiate_call` with `answer_url = f"{public_base_url}/plivo/voice?call_id={call.id}&agent_id={agent_id}&lang={lang}"`.
       - On failure: roll back credit reservation, mark call failed, and raise descriptive error.
   - In `backend/api/v1/calls.py` `hangup_call`:
     - If `call.get("provider") == "plivo"`, call `hangup_plivo_call(call_id, db=db)`.

6. **Admin Dashboard UI (`frontend/app/(admin)/admin/phone-numbers/page.tsx`)**:
   - Add `"plivo"` to provider options in "Add Number" modal.
   - When `"plivo"` is selected, display credential inputs:
     - `Plivo Auth ID` (required)
     - `Plivo Auth Token` (required, with show/hide password toggle)
     - `Plivo App / Subaccount ID` (optional)
   - Store these in `provider_metadata` as `plivo_auth_id`, `plivo_auth_token`, and `plivo_app_id`.
   - Display a blue-themed badge in the phone number inventory table for `"plivo"`.

"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Users,
  Search,
  Upload,
  ArrowRight,
  ArrowLeft,
  CheckSquare,
  Square,
  Check,
  Tag,
  MapPin,
  Filter,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { StatusBadge } from "@/components/ui/badge";
import { api, Lead } from "@/lib/api";
import { InlineLeadUploadModal } from "./inline-lead-upload-modal";

const PAGE_SIZE = 25;

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "new", label: "New (Never Contacted)" },
  { value: "contacted", label: "Contacted" },
  { value: "qualified", label: "Qualified" },
  { value: "callback", label: "Callback" },
  { value: "not_interested", label: "Not Interested" },
  { value: "failed", label: "Failed Attempts" },
];

interface StepContactsProps {
  selectedLeadIds: string[];
  selectAllMatched: boolean;
  onToggleLead: (leadId: string) => void;
  onSetSelectedLeads: (leadIds: string[]) => void;
  onSetSelectAllMatched: (selectAll: boolean) => void;
  onBack: () => void;
  onNext: () => void;
}

export function StepContacts({
  selectedLeadIds,
  selectAllMatched,
  onToggleLead,
  onSetSelectedLeads,
  onSetSelectAllMatched,
  onBack,
  onNext,
}: StepContactsProps) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [totalLeads, setTotalLeads] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  // Filters
  const [search, setSearch] = useState("");
  const [selectedCity, setSelectedCity] = useState("");
  const [selectedTag, setSelectedTag] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("");

  // Metadata filter options
  const [cities, setCities] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Load filter options
  const loadFilters = useCallback(() => {
    api.leads
      .filters()
      .then((data) => {
        setCities(data.cities || []);
        setAvailableTags(data.tags || []);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadFilters();
  }, [loadFilters]);

  // Load leads
  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.leads.list({
        search: search.trim() || undefined,
        city: selectedCity || undefined,
        tag: selectedTag || undefined,
        status: selectedStatus || undefined,
        limit: PAGE_SIZE,
        skip: (page - 1) * PAGE_SIZE,
      });
      setLeads(res.leads);
      setTotalLeads(res.total);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to load contacts");
    } finally {
      setLoading(false);
    }
  }, [search, selectedCity, selectedTag, selectedStatus, page]);

  useEffect(() => {
    setPage(1);
  }, [search, selectedCity, selectedTag, selectedStatus]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // Handle master select all for current page vs all matched
  const isAllCurrentPageSelected =
    leads.length > 0 && leads.every((l) => selectedLeadIds.includes(l.id));

  function toggleSelectCurrentPage() {
    if (selectAllMatched) {
      onSetSelectAllMatched(false);
      onSetSelectedLeads([]);
      return;
    }

    if (isAllCurrentPageSelected) {
      // Deselect current page
      const pageIds = new Set(leads.map((l) => l.id));
      onSetSelectedLeads(selectedLeadIds.filter((id) => !pageIds.has(id)));
    } else {
      // Select current page
      const currentSet = new Set(selectedLeadIds);
      leads.forEach((l) => currentSet.add(l.id));
      onSetSelectedLeads(Array.from(currentSet));
    }
  }

  function handleSelectAllMatchedToggle() {
    if (selectAllMatched) {
      onSetSelectAllMatched(false);
      onSetSelectedLeads([]);
    } else {
      onSetSelectAllMatched(true);
      toast.success(`Selected all ${totalLeads} matching contacts!`);
    }
  }

  function handleUploadSuccess(importedCount: number, appliedTags?: string[]) {
    loadFilters();
    fetchLeads();
    if (appliedTags && appliedTags.length > 0) {
      setSelectedTag(appliedTags[0]);
    }
    toast.success(`Added ${importedCount} contacts to campaign selection`);
  }

  function handleProceedNext() {
    const totalSelected = selectAllMatched ? totalLeads : selectedLeadIds.length;
    if (totalSelected === 0) {
      toast.error("Please select at least one contact for this campaign");
      return;
    }
    onNext();
  }

  const effectiveCount = selectAllMatched ? totalLeads : selectedLeadIds.length;
  const totalPages = Math.ceil(totalLeads / PAGE_SIZE) || 1;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-primary/10 text-brand-primary font-bold text-sm">
                4
              </div>
              <div>
                <h3 className="text-base font-semibold text-text-primary">
                  Select Campaign Audience
                </h3>
                <p className="text-xs text-text-secondary">
                  Filter by city, tags, or status, and choose which leads to dial in this campaign.
                </p>
              </div>
            </div>

            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowUploadModal(true)}
              className="gap-1.5 border-brand-primary/30 text-brand-primary hover:bg-brand-primary/10 self-start sm:self-auto"
            >
              <Upload className="h-4 w-4" />
              Upload New Contacts
            </Button>
          </div>
        </CardHeader>

        <CardBody className="space-y-4">
          {/* Filter Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 bg-bg-subtle/70 p-3 rounded-xl border border-border-default">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search name, phone..."
                className="pl-9 text-xs"
              />
            </div>

            {/* City Filter */}
            <div className="relative">
              <Select
                value={selectedCity}
                onChange={(e) => setSelectedCity(e.target.value)}
                className="text-xs"
              >
                <option value="">All Cities</option>
                {cities.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
            </div>

            {/* Tag Filter */}
            <div className="relative">
              <Select
                value={selectedTag}
                onChange={(e) => setSelectedTag(e.target.value)}
                className="text-xs"
              >
                <option value="">All Tags</option>
                {availableTags.map((t) => (
                  <option key={t} value={t}>
                    #{t}
                  </option>
                ))}
              </Select>
            </div>

            {/* Status Filter */}
            <div>
              <Select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="text-xs"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {/* Selection Banner & Bulk Controls */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-brand-primary/5 border border-brand-primary/20">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSelectAllMatchedToggle}
                className="flex items-center gap-2 text-xs font-semibold text-brand-primary hover:underline"
              >
                {selectAllMatched ? (
                  <CheckSquare className="h-4 w-4 fill-current text-brand-primary" />
                ) : (
                  <Square className="h-4 w-4 text-brand-primary" />
                )}
                Select All Matched Contacts ({totalLeads.toLocaleString()})
              </button>

              <span className="text-xs text-text-muted">|</span>

              <span className="text-xs font-semibold text-text-primary">
                {effectiveCount.toLocaleString()} contact{effectiveCount !== 1 ? "s" : ""} selected
              </span>
            </div>

            {effectiveCount > 0 && !selectAllMatched && (
              <button
                type="button"
                onClick={() => onSetSelectedLeads([])}
                className="text-xs text-text-muted hover:text-accent-red underline"
              >
                Clear Selection
              </button>
            )}
          </div>

          {/* Leads Table */}
          <div className="rounded-xl border border-border-default overflow-hidden bg-bg-surface">
            {loading ? (
              <div className="flex items-center justify-center py-16 gap-2 text-xs text-text-muted">
                <Spinner size="md" />
                Loading contacts...
              </div>
            ) : leads.length === 0 ? (
              <div className="p-12 text-center">
                <Users className="h-10 w-10 text-text-muted mx-auto mb-2 opacity-40" />
                <p className="text-sm font-semibold text-text-primary">
                  No contacts found
                </p>
                <p className="text-xs text-text-muted mt-1 max-w-sm mx-auto">
                  No leads match your current search and filter criteria. Try clearing filters or upload a new contact list.
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowUploadModal(true)}
                  className="mt-4 gap-1.5 text-xs"
                >
                  <Upload className="h-3.5 w-3.5" />
                  Upload Contacts
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-border-default bg-bg-subtle/50 text-text-secondary">
                      <th className="py-2.5 px-3 w-10 text-center">
                        <input
                          type="checkbox"
                          checked={selectAllMatched || isAllCurrentPageSelected}
                          onChange={toggleSelectCurrentPage}
                          className="rounded border-border-default text-brand-primary focus:ring-brand-primary cursor-pointer"
                        />
                      </th>
                      <th className="py-2.5 px-3 font-semibold">Contact</th>
                      <th className="py-2.5 px-3 font-semibold">Location / City</th>
                      <th className="py-2.5 px-3 font-semibold">Tags</th>
                      <th className="py-2.5 px-3 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {leads.map((lead) => {
                      const isSelected =
                        selectAllMatched || selectedLeadIds.includes(lead.id);
                      const city =
                        lead.custom_fields?.city ||
                        lead.custom_fields?.Town ||
                        "";

                      return (
                        <tr
                          key={lead.id}
                          onClick={() => {
                            if (selectAllMatched) {
                              onSetSelectAllMatched(false);
                              onSetSelectedLeads(
                                leads
                                  .map((l) => l.id)
                                  .filter((id) => id !== lead.id)
                              );
                            } else {
                              onToggleLead(lead.id);
                            }
                          }}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? "bg-brand-primary/5 hover:bg-brand-primary/10"
                              : "hover:bg-bg-subtle/60"
                          }`}
                        >
                          <td
                            className="py-2.5 px-3 text-center"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => {
                                if (selectAllMatched) {
                                  onSetSelectAllMatched(false);
                                  onSetSelectedLeads(
                                    leads
                                      .map((l) => l.id)
                                      .filter((id) => id !== lead.id)
                                  );
                                } else {
                                  onToggleLead(lead.id);
                                }
                              }}
                              className="rounded border-border-default text-brand-primary focus:ring-brand-primary cursor-pointer"
                            />
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="font-semibold text-text-primary block">
                              {lead.name || lead.phone}
                            </span>
                            {lead.name && (
                              <span className="text-[11px] text-text-muted font-mono block">
                                {lead.phone}
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-text-secondary">
                            {city ? (
                              <span className="inline-flex items-center gap-1">
                                <MapPin className="h-3 w-3 text-text-muted" />
                                {String(city)}
                              </span>
                            ) : (
                              <span className="text-text-muted">—</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            {lead.tags && lead.tags.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {lead.tags.slice(0, 3).map((tag) => (
                                  <span
                                    key={tag}
                                    className="bg-bg-subtle px-1.5 py-0.5 rounded text-[10px] text-text-secondary border border-border-default"
                                  >
                                    #{tag}
                                  </span>
                                ))}
                                {lead.tags.length > 3 && (
                                  <span className="text-[10px] text-text-muted">
                                    +{lead.tags.length - 3}
                                  </span>
                                )}
                              </div>
                            ) : (
                              <span className="text-text-muted">—</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            <StatusBadge status={lead.status} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between p-3 border-t border-border-default bg-bg-subtle/30 text-xs">
                <span className="text-text-muted">
                  Page {page} of {totalPages} ({totalLeads.toLocaleString()} total)
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="text-xs h-7 px-2"
                  >
                    Previous
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    className="text-xs h-7 px-2"
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardBody>
      </Card>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between pt-2">
        <Button
          type="button"
          variant="ghost"
          onClick={onBack}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back: Calling Schedule
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={handleProceedNext}
          className="gap-2 px-6"
        >
          Next: Review & Launch
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Inline Upload Modal */}
      <InlineLeadUploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onSuccess={handleUploadSuccess}
      />
    </div>
  );
}

"use client";

import React from "react";
import { PostSyncInsightLibrary } from "@/components/insights/PostSyncInsightLibrary";

export default function InsightsPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        <PostSyncInsightLibrary />
      </div>
    </main>
  );
}

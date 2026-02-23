/**
 * Polls jobs and shows toast notifications when jobs complete or fail.
 * Respects user notification preferences from Settings.
 */
import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";
import { getNotificationPrefs } from "@/components/Layout";

const POLL_INTERVAL_MS = 5000;
const SEEN_JOBS_KEY = "tdm-seen-job-ids";

function getSeenJobIds(): Set<string> {
  try {
    const s = sessionStorage.getItem(SEEN_JOBS_KEY);
    if (s) return new Set(JSON.parse(s));
  } catch {}
  return new Set<string>();
}

function markJobSeen(jobId: string) {
  const seen = getSeenJobIds();
  seen.add(jobId);
  try {
    sessionStorage.setItem(SEEN_JOBS_KEY, JSON.stringify([...seen].slice(-200)));
  } catch {}
}

export function useJobNotifications() {
  const queryClient = useQueryClient();
  const lastJobsRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const jobs = await api.listJobs();
        const prefs = getNotificationPrefs();
        const seen = getSeenJobIds();

        for (const job of jobs) {
          const key = job.id;
          const prev = lastJobsRef.current.get(key);
          lastJobsRef.current.set(key, job.status);

          // Only notify on transition to completed/failed
          if (prev === "running" || prev === "pending") {
            if (job.status === "completed") {
              if (prefs.jobComplete && !seen.has(key)) {
                markJobSeen(key);
                toast.success(`Job completed`, {
                  description: `${job.operation} (${key.slice(0, 8)}) finished successfully`,
                  duration: 5000,
                });
                queryClient.invalidateQueries({ queryKey: ["jobs"] });
                queryClient.invalidateQueries({ queryKey: ["datasets"] });
                queryClient.invalidateQueries({ queryKey: ["target-tables"] });
              }
            } else if (job.status === "failed") {
              if (prefs.jobFailed && !seen.has(key)) {
                markJobSeen(key);
                const err = (job as { result_json?: { error?: string } }).result_json?.error;
                toast.error(`Job failed`, {
                  description: `${job.operation} (${key.slice(0, 8)}): ${err || "Unknown error"}`,
                  duration: 8000,
                });
                queryClient.invalidateQueries({ queryKey: ["jobs"] });
              }
            }
          }
        }
      } catch {
        // Ignore poll errors (backend may be down)
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [queryClient]);
}

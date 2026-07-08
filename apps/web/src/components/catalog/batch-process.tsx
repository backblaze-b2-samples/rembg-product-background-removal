"use client";

import { Layers } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useRunPending } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";

export function BatchProcess({ pendingCount }: { pendingCount: number }) {
  const mut = useRunPending();

  const onClick = async () => {
    try {
      const result = await mut.mutateAsync();
      if (result.processed === 0 && result.failed === 0) {
        toast.info("Nothing pending — every product already has a cutout.");
      } else {
        toast.success(
          `Processed ${result.processed} product(s)` +
            (result.failed ? `, ${result.failed} failed` : ""),
        );
      }
    } catch (e) {
      toast.error(
        e instanceof ApiError ? e.message : "Batch removal failed",
      );
    }
  };

  return (
    <Button
      size="sm"
      variant="outline"
      className="h-8"
      onClick={onClick}
      disabled={mut.isPending || pendingCount === 0}
      title={
        pendingCount === 0
          ? "No pending products"
          : `Run rembg on ${pendingCount} pending product(s)`
      }
    >
      <Layers className="h-3.5 w-3.5" />
      {mut.isPending
        ? "Processing..."
        : `Process all pending${pendingCount ? ` (${pendingCount})` : ""}`}
    </Button>
  );
}

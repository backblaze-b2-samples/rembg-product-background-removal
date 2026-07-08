"use client";

import { Scissors, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useRunRemoval } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";

export function RemoveButton({
  sku,
  hasCutout,
  size = "sm",
  variant,
}: {
  sku: string;
  hasCutout: boolean;
  size?: "sm" | "default";
  variant?: "default" | "outline" | "secondary";
}) {
  const mut = useRunRemoval();

  const onClick = async () => {
    try {
      const result = await mut.mutateAsync(sku);
      toast.success(
        `Cutout ready for ${sku} (${result.sidecar.processing_ms} ms)`,
      );
    } catch (e) {
      // 503 = ML deps not installed — surface the actionable hint verbatim.
      toast.error(
        e instanceof ApiError ? e.message : "Background removal failed",
      );
    }
  };

  const Icon = hasCutout ? RefreshCw : Scissors;
  return (
    <Button
      size={size}
      variant={variant ?? (hasCutout ? "outline" : "default")}
      onClick={onClick}
      disabled={mut.isPending}
    >
      <Icon className="h-3.5 w-3.5" />
      {mut.isPending
        ? "Removing..."
        : hasCutout
          ? "Re-run"
          : "Remove background"}
    </Button>
  );
}

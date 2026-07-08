"use client";

import { PackageOpen, Scissors, Clock, HardDrive } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useCatalogStats } from "@/lib/queries";

export function CatalogStatsCards() {
  const { data: stats, isLoading, error, refetch } = useCatalogStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards: {
    title: string;
    value: string | number;
    icon: LucideIcon;
    hint?: string;
  }[] = [
    {
      title: "Products",
      value: stats?.total_products ?? 0,
      icon: PackageOpen,
    },
    {
      title: "Cutouts produced",
      value: stats?.cutouts_produced ?? 0,
      icon: Scissors,
      hint: stats ? `avg ${stats.avg_processing_ms} ms / cutout` : undefined,
    },
    {
      title: "Pending",
      value: stats?.pending ?? 0,
      icon: Clock,
    },
    {
      title: "Cutout storage",
      value: stats?.cutouts_human ?? "0 B",
      icon: HardDrive,
      hint: stats
        ? `orig ${stats.originals_human} · ${stats.amplification_ratio}× total`
        : undefined,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="stat-value">{card.value}</div>
                {card.hint && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {card.hint}
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CatalogStatsCards } from "@/components/dashboard/catalog-stats-cards";
import { RecentCutoutsTable } from "@/components/dashboard/recent-cutouts-table";
import { CutoutChart } from "@/components/dashboard/cutout-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Background-removal catalog overview — products, cutouts, and the
            storage each cutout adds on Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/products/new">
            <Plus className="h-3.5 w-3.5" />
            New product
          </Link>
        </Button>
      </div>
      <CatalogStatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <CutoutChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentCutoutsTable />
        </div>
      </div>
    </div>
  );
}

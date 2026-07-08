"use client";

import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProductTable } from "@/components/catalog/product-table";
import { BatchProcess } from "@/components/catalog/batch-process";
import { CsvImport } from "@/components/catalog/csv-import";
import { useCatalogStats } from "@/lib/queries";

export default function CatalogPage() {
  const { data: stats } = useCatalogStats();
  const pending = stats?.pending ?? 0;

  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Catalog</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Products scoped to <code>products/</code> in your bucket. Create a
            product, run rembg, and store the transparent cutout back on B2.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <CsvImport />
          <BatchProcess pendingCount={pending} />
          <Button asChild size="sm" className="h-8">
            <Link href="/products/new">
              <Plus className="h-3.5 w-3.5" />
              New product
            </Link>
          </Button>
        </div>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <Card>
          <CardContent className="p-0">
            <ProductTable />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

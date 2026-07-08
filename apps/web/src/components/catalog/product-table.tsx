"use client";

import Link from "next/link";
import { PackageOpen, ImageOff } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useProducts } from "@/lib/queries";
import type { Product } from "@rembg-product-background-removal/shared";

function StatusBadge({ status }: { status: Product["status"] }) {
  if (status === "done") {
    return (
      <Badge variant="outline" className="gap-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" />
        Cutout ready
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="gap-1.5">
      <span className="h-1.5 w-1.5 rounded-full bg-[var(--attention)]" />
      Pending
    </Badge>
  );
}

function Thumb({ product }: { product: Product }) {
  if (!product.thumbnail_url) {
    return (
      <div className="checkerboard flex h-10 w-10 items-center justify-center rounded border border-border">
        <ImageOff className="h-4 w-4 text-muted-foreground" />
      </div>
    );
  }
  return (
    <div className="checkerboard h-10 w-10 overflow-hidden rounded border border-border">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={product.thumbnail_url}
        alt={product.sku}
        className="h-full w-full object-contain"
      />
    </div>
  );
}

export function ProductTable() {
  const { data: products = [], isLoading, error, refetch } = useProducts();

  if (isLoading) {
    return (
      <div className="space-y-3 p-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }
  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }
  if (products.length === 0) {
    return (
      <EmptyState
        icon={PackageOpen}
        title="No products yet"
        description="Create a product or import a CSV manifest to start building cutouts."
        action={
          <Button asChild size="sm">
            <Link href="/products/new">New product</Link>
          </Button>
        }
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="bg-muted/40 hover:bg-muted/40">
          <TableHead className="w-[64px]">Preview</TableHead>
          <TableHead>SKU</TableHead>
          <TableHead>Category</TableHead>
          <TableHead>Batch</TableHead>
          <TableHead>Model</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {products.map((p) => (
          <TableRow key={p.sku} className="table-row-hover">
            <TableCell>
              <Thumb product={p} />
            </TableCell>
            <TableCell className="font-medium">
              <Link
                href={`/products/${encodeURIComponent(p.sku)}`}
                className="hover:underline"
              >
                {p.sku}
              </Link>
            </TableCell>
            <TableCell className="text-muted-foreground">{p.category}</TableCell>
            <TableCell className="text-muted-foreground">
              {p.batch ?? "—"}
            </TableCell>
            <TableCell className="font-mono text-xs text-muted-foreground">
              {p.model}
            </TableCell>
            <TableCell>
              <StatusBadge status={p.status} />
            </TableCell>
            <TableCell className="text-right">
              <Button asChild size="sm" variant="ghost">
                <Link href={`/products/${encodeURIComponent(p.sku)}`}>
                  View
                </Link>
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

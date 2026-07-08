"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ProductDetailView } from "@/components/catalog/product-detail";

export default function ProductDetailPage() {
  const params = useParams<{ sku: string }>();
  const sku = decodeURIComponent(
    Array.isArray(params.sku) ? params.sku[0] : params.sku,
  );

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <Button asChild variant="ghost" size="sm" className="mb-2 -ml-2 h-7">
          <Link href="/products">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to catalog
          </Link>
        </Button>
        <h1 className="page-title">Product</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Before/after cutout, sidecar metadata, and lifecycle actions.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <ProductDetailView sku={sku} />
      </div>
    </div>
  );
}

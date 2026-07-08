"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Download, ImageOff, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useProduct, useDeleteProduct } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";
import type { ProductDetail as ProductDetailT } from "@rembg-product-background-removal/shared";
import { RemoveButton } from "./remove-button";
import { ProductForm } from "./product-form";

function ImagePane({
  title,
  url,
  checker,
}: {
  title: string;
  url: string | null;
  checker?: boolean;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </p>
      <div
        className={`flex aspect-square w-full items-center justify-center overflow-hidden rounded-md border border-border ${
          checker ? "checkerboard" : "bg-muted/30"
        }`}
      >
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt={title} className="h-full w-full object-contain" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <ImageOff className="h-6 w-6" />
            <span className="text-sm">No cutout yet</span>
          </div>
        )}
      </div>
    </div>
  );
}

function SidecarPanel({ product }: { product: ProductDetailT }) {
  const s = product.sidecar;
  const rows: [string, string][] = [
    ["Status", product.status === "done" ? "Cutout ready" : "Pending"],
    ["Model", product.model],
    ["Alpha matting", product.alpha_matting ? "On" : "Off"],
    ["Category", product.category],
    ["Batch", product.batch ?? "—"],
  ];
  if (s) {
    rows.push(
      ["rembg version", s.rembg_version],
      ["Processing time", `${s.processing_ms} ms`],
      ["Dimensions", `${s.width} × ${s.height}px`],
      [
        "Foreground coverage",
        `${(s.foreground_ratio * 100).toFixed(1)}% (alpha-coverage proxy, not a confidence score)`,
      ],
    );
  }
  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Cutout metadata (sidecar)</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <dl className="divide-y divide-border">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 px-5 py-2.5">
              <dt className="text-sm text-muted-foreground">{k}</dt>
              <dd className="text-sm font-medium text-right">{v}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

export function ProductDetailView({ sku }: { sku: string }) {
  const router = useRouter();
  const { data: product, isLoading, error, refetch } = useProduct(sku);
  const deleteMut = useDeleteProduct();
  const [editOpen, setEditOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="aspect-square w-full" />
        <Skeleton className="aspect-square w-full" />
      </div>
    );
  }
  if (error || !product) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const hasCutout = product.status === "done";

  const onDelete = async () => {
    try {
      await deleteMut.mutateAsync(product.sku);
      toast.success(`Deleted ${product.sku}`);
      router.push("/products");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Delete failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="section-title">{product.sku}</h2>
          <Badge variant={hasCutout ? "outline" : "secondary"}>
            {hasCutout ? "Cutout ready" : "Pending"}
          </Badge>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <RemoveButton sku={product.sku} hasCutout={hasCutout} />
          <Button
            size="sm"
            variant="outline"
            onClick={() => setEditOpen(true)}
          >
            <Pencil className="h-3.5 w-3.5" />
            Edit
          </Button>
          {product.cutout_url && (
            <Button asChild size="sm" variant="outline">
              <a href={product.cutout_url} download>
                <Download className="h-3.5 w-3.5" />
                Download cutout
              </a>
            </Button>
          )}
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="outline">
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete {product.sku}?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently removes the original, its cutout and sidecar,
                  and the catalog record from B2. Only this SKU&apos;s objects
                  are deleted. This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={onDelete}>
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ImagePane title="Original" url={product.original_url} />
        <ImagePane title="Cutout" url={product.cutout_url} checker />
      </div>

      <SidecarPanel product={product} />

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit {product.sku}</DialogTitle>
          </DialogHeader>
          <ProductForm
            mode="edit"
            product={product}
            onDone={() => {
              setEditOpen(false);
              refetch();
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}

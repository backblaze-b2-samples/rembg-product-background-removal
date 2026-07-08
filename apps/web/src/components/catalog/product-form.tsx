"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  PRODUCT_CATEGORIES,
  REMBG_MODELS,
  type ProductDetail,
} from "@rembg-product-background-removal/shared";
import { useCreateProduct, useUpdateProduct } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";

// Human-friendly labels for the finite model selector.
const MODEL_LABELS: Record<string, string> = {
  u2net: "u2net (general purpose)",
  u2netp: "u2netp (lightweight / fast)",
  "isnet-general-use": "isnet-general-use (sharper edges)",
  u2net_human_seg: "u2net_human_seg (people)",
  silueta: "silueta (compact)",
};

const SKU_PATTERN = /^[A-Za-z0-9._-]+$/;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

const schema = z.object({
  category: z.string(),
  batch: z.string().max(64, "Batch must be 64 characters or fewer").optional(),
  model: z.string(),
  alpha_matting: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

export function ProductForm({
  mode,
  product,
  onDone,
}: {
  mode: "create" | "edit";
  product?: ProductDetail;
  // When provided (e.g. inside the edit dialog), called after a successful
  // save instead of navigating. Falls back to router navigation otherwise.
  onDone?: () => void;
}) {
  const router = useRouter();
  const createMut = useCreateProduct();
  const updateMut = useUpdateProduct(product?.sku ?? "");

  const [sku, setSku] = useState(product?.sku ?? "");
  const [skuError, setSkuError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [removeNow, setRemoveNow] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      category: product?.category ?? "Apparel",
      batch: product?.batch ?? "",
      model: product?.model ?? "u2net",
      alpha_matting: product?.alpha_matting ?? false,
    },
  });

  const submitting = createMut.isPending || updateMut.isPending;

  const onSubmit = async (values: FormValues) => {
    if (mode === "create") {
      let ok = true;
      if (!SKU_PATTERN.test(sku)) {
        setSkuError("Letters, digits, dots, dashes and underscores only.");
        ok = false;
      }
      if (!file) {
        setFileError("Choose a product image (JPEG, PNG or WebP).");
        ok = false;
      }
      if (!ok || !file) return;

      try {
        await createMut.mutateAsync({
          file,
          sku,
          category: values.category,
          batch: values.batch,
          model: values.model,
          alpha_matting: values.alpha_matting,
          remove_now: removeNow,
        });
        toast.success(`Product "${sku}" created`);
        if (onDone) onDone();
        else router.push(`/products/${encodeURIComponent(sku)}`);
      } catch (e) {
        toast.error(
          e instanceof ApiError ? e.message : "Failed to create product",
        );
      }
      return;
    }

    // edit
    try {
      await updateMut.mutateAsync({
        category: values.category,
        batch: values.batch || null,
        model: values.model,
        alpha_matting: values.alpha_matting,
      });
      toast.success("Product updated");
      if (onDone) onDone();
      else router.push(`/products/${encodeURIComponent(product!.sku)}`);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Failed to update product");
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">
              {mode === "create" ? "New product" : `Edit ${product?.sku}`}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 space-y-6">
            {/* SKU */}
            <div className="space-y-2">
              <FormLabel htmlFor="sku">SKU</FormLabel>
              <Input
                id="sku"
                value={sku}
                disabled={mode === "edit"}
                placeholder="SKU-1001"
                onChange={(e) => {
                  setSku(e.target.value);
                  setSkuError(null);
                }}
              />
              {mode === "create" ? (
                <FormDescription>
                  Unique identifier and B2 key, e.g. <code>SKU-1001</code>.
                </FormDescription>
              ) : (
                <FormDescription>
                  SKU is the B2 object key and cannot be changed (renaming would
                  move objects — out of scope).
                </FormDescription>
              )}
              {skuError && (
                <p className="text-sm text-destructive">{skuError}</p>
              )}
            </div>

            {/* Image (create only) */}
            {mode === "create" && (
              <div className="space-y-2">
                <FormLabel htmlFor="image">Product image</FormLabel>
                <Input
                  id="image"
                  type="file"
                  accept={ACCEPTED_TYPES.join(",")}
                  onChange={(e) => {
                    setFile(e.target.files?.[0] ?? null);
                    setFileError(null);
                  }}
                />
                <FormDescription>
                  Safe test run: upload one JPEG/PNG product photo, keep model{" "}
                  <code>u2net</code>, leave alpha-matting off.
                </FormDescription>
                {fileError && (
                  <p className="text-sm text-destructive">{fileError}</p>
                )}
              </div>
            )}

            {/* Category */}
            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Category</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger className="w-64">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {PRODUCT_CATEGORIES.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {mode === "create" && (
                    <FormDescription>Defaults to Apparel.</FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Model */}
            <FormField
              control={form.control}
              name="model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Removal model</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger className="w-72">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {REMBG_MODELS.map((m) => (
                        <SelectItem key={m} value={m}>
                          {MODEL_LABELS[m] ?? m}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {mode === "create" && (
                    <FormDescription>
                      Defaults to u2net (general purpose).
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Batch */}
            <FormField
              control={form.control}
              name="batch"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Batch (optional)</FormLabel>
                  <FormControl>
                    <Input
                      className="w-64"
                      placeholder="2026-summer"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Alpha matting */}
            <FormField
              control={form.control}
              name="alpha_matting"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-md border border-border p-3">
                  <div className="space-y-0.5">
                    <FormLabel>Alpha matting</FormLabel>
                    <FormDescription>
                      Finer edges via pymatting. Slower; off by default.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            {/* Remove now (create only) */}
            {mode === "create" && (
              <div className="flex flex-row items-center justify-between rounded-md border border-border p-3">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">Remove background now</p>
                  <p className="text-sm text-muted-foreground">
                    Run the cutout immediately after upload (else it stays
                    pending).
                  </p>
                </div>
                <Switch checked={removeNow} onCheckedChange={setRemoveNow} />
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => (onDone ? onDone() : router.back())}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting
              ? "Saving..."
              : mode === "create"
                ? "Create product"
                : "Save changes"}
          </Button>
        </div>
      </form>
    </Form>
  );
}

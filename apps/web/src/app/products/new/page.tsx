import { ProductForm } from "@/components/catalog/product-form";

export default function NewProductPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New product</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Register an SKU with its product photo. The original lands in B2; run
          the cutout now or later.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2 max-w-2xl">
        <ProductForm mode="create" />
      </div>
    </div>
  );
}

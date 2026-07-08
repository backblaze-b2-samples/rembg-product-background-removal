"use client";

import { useState } from "react";
import { FileUp } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { useImportProducts } from "@/lib/queries";
import { ApiError } from "@/lib/api-client";

export function CsvImport() {
  const [open, setOpen] = useState(false);
  const [manifest, setManifest] = useState<File | null>(null);
  const [images, setImages] = useState<File[]>([]);
  const mut = useImportProducts();

  const onImport = async () => {
    if (!manifest) {
      toast.error("Choose a CSV manifest first.");
      return;
    }
    try {
      const result = await mut.mutateAsync({ manifest, files: images });
      toast.success(
        `Imported ${result.created} product(s), skipped ${result.skipped}.`,
      );
      setOpen(false);
      setManifest(null);
      setImages([]);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Import failed");
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" className="h-8">
          <FileUp className="h-3.5 w-3.5" />
          Import CSV
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Batch ingest from a CSV manifest</DialogTitle>
          <DialogDescription>
            Upload a CSV with columns{" "}
            <code>sku,category,batch,filename</code> plus the matching image
            files. Each row registers a product as <strong>pending</strong>;
            run &quot;Process all pending&quot; afterwards to cut them out.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="manifest">CSV manifest</Label>
            <Input
              id="manifest"
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setManifest(e.target.files?.[0] ?? null)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="images">Image files</Label>
            <Input
              id="images"
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setImages(Array.from(e.target.files ?? []))}
            />
            <p className="text-xs text-muted-foreground">
              {images.length
                ? `${images.length} image(s) selected`
                : "Filenames must match the manifest's filename column."}
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={mut.isPending}
          >
            Cancel
          </Button>
          <Button onClick={onImport} disabled={mut.isPending || !manifest}>
            {mut.isPending ? "Importing..." : "Import"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Product catalog (rembg background removal) ---

export type ProductStatus = "pending" | "done";

export const REMBG_MODELS = [
  "u2net",
  "u2netp",
  "isnet-general-use",
  "u2net_human_seg",
  "silueta",
] as const;
export type RembgModel = (typeof REMBG_MODELS)[number];

export const PRODUCT_CATEGORIES = [
  "Apparel",
  "Footwear",
  "Accessories",
  "Electronics",
  "Home",
  "Beauty",
  "Other",
] as const;
export type ProductCategory = (typeof PRODUCT_CATEGORIES)[number];

export interface RemovalSidecar {
  model: string;
  rembg_version: string;
  processing_ms: number;
  width: number;
  height: number;
  // Honest coverage proxy (fraction of pixels above alpha threshold), NOT a
  // model confidence score.
  foreground_ratio: number;
  alpha_matting: boolean;
  created_at: string;
}

export interface Product {
  sku: string;
  category: string;
  batch: string | null;
  original_filename: string;
  original_key: string;
  model: string;
  alpha_matting: boolean;
  status: ProductStatus;
  created_at: string;
  updated_at: string;
  cutout_key: string | null;
  thumbnail_url: string | null;
}

export interface ProductDetail extends Product {
  original_url: string | null;
  cutout_url: string | null;
  sidecar: RemovalSidecar | null;
}

export interface RemovalResult {
  sku: string;
  cutout_key: string;
  sidecar: RemovalSidecar;
}

export interface BatchRemovalResult {
  processed: number;
  failed: number;
  results: RemovalResult[];
}

export interface CatalogStats {
  total_products: number;
  cutouts_produced: number;
  pending: number;
  originals_bytes: number;
  originals_human: string;
  cutouts_bytes: number;
  cutouts_human: string;
  amplification_ratio: number;
  avg_processing_ms: number;
}

export interface DailyCutoutCount {
  date: string;
  cutouts: number;
}

export interface ImportRow {
  sku: string;
  status: string;
  detail: string | null;
}

export interface ImportResult {
  created: number;
  skipped: number;
  rows: ImportRow[];
}

export interface ProductUpdate {
  category?: string;
  batch?: string | null;
  model?: string;
  alpha_matting?: boolean;
}

import mongoose, { Schema, Document } from 'mongoose';
import { ENV } from '../config/env';

export interface IDnsCache extends Document {
  domain: string;
  type: string;
  records: Record<string, unknown>[];
  queryTimeMs: number;
  createdAt: Date;
}

const DnsCacheSchema = new Schema<IDnsCache>(
  {
    domain: { type: String, required: true },
    type: { type: String, required: true },
    records: { type: Schema.Types.Mixed, required: true },
    queryTimeMs: { type: Number, required: true },
    createdAt: { type: Date, default: Date.now, expires: ENV.CACHE_TTL_SECONDS },
  },
  { versionKey: false }
);

DnsCacheSchema.index({ domain: 1, type: 1 }, { unique: true });

export const DnsCache = mongoose.model<IDnsCache>('DnsCache', DnsCacheSchema);

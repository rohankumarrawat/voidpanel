import mongoose, { Document } from 'mongoose';
export interface IDnsCache extends Document {
    domain: string;
    type: string;
    records: Record<string, unknown>[];
    queryTimeMs: number;
    createdAt: Date;
}
export declare const DnsCache: mongoose.Model<IDnsCache, {}, {}, {}, mongoose.Document<unknown, {}, IDnsCache, {}, {}> & IDnsCache & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
}, any>;
//# sourceMappingURL=DnsCache.d.ts.map
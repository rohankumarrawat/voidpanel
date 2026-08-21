import mongoose, { Document } from 'mongoose';
export interface ILookupHistory extends Document {
    domain: string;
    type: string;
    status: 'success' | 'not_found' | 'error';
    timestamp: Date;
    ipHash: string;
}
export declare const LookupHistory: mongoose.Model<ILookupHistory, {}, {}, {}, mongoose.Document<unknown, {}, ILookupHistory, {}, {}> & ILookupHistory & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
}, any>;
//# sourceMappingURL=LookupHistory.d.ts.map
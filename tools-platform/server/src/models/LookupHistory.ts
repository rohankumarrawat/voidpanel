import mongoose, { Schema, Document } from 'mongoose';

export interface ILookupHistory extends Document {
  domain: string;
  type: string;
  status: 'success' | 'not_found' | 'error';
  timestamp: Date;
  ipHash: string;
}

const LookupHistorySchema = new Schema<ILookupHistory>(
  {
    domain: { type: String, required: true, index: true },
    type: { type: String, required: true },
    status: {
      type: String,
      required: true,
      enum: ['success', 'not_found', 'error'],
    },
    timestamp: { type: Date, default: Date.now, index: -1 },
    ipHash: { type: String, required: true },
  },
  { versionKey: false }
);

export const LookupHistory = mongoose.model<ILookupHistory>(
  'LookupHistory',
  LookupHistorySchema
);

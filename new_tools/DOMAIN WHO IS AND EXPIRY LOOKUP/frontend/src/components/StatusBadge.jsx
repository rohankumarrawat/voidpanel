import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Lock, Sparkles } from 'lucide-react';

export default function StatusBadge({ status, isAvailable, privacyProtected }) {
  let label = 'Active';
  let colorStyle = 'bg-emerald-50 border-emerald-200 text-emerald-700';
  let Icon = CheckCircle2;

  if (isAvailable || status === 'available') {
    label = 'Available (Unregistered)';
    colorStyle = 'bg-blue-50 border-blue-200 text-blue-700';
    Icon = Sparkles;
  } else if (status === 'expired') {
    label = 'Expired';
    colorStyle = 'bg-red-50 border-red-200 text-red-700';
    Icon = XCircle;
  } else if (status === 'expiring') {
    label = 'Expiring Soon';
    colorStyle = 'bg-amber-50 border-amber-200 text-amber-700';
    Icon = AlertTriangle;
  } else if (status === 'privacy_protected' || privacyProtected) {
    label = 'Privacy-Protected';
    colorStyle = 'bg-purple-50 border-purple-200 text-purple-700';
    Icon = Lock;
  }

  return (
    <div className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-full border text-xs font-mono font-semibold tracking-wide ${colorStyle}`}>
      <Icon className="w-3.5 h-3.5" />
      <span>{label}</span>
    </div>
  );
}

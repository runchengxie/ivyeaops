export function cleanPayload(value: unknown): Record<string, unknown>;
export function safeEvidenceUrl(value: string): string | null;

export function mergeVerifiedHistory<T extends {record_id:string;revision:number;current:boolean}>(head:T[],older:T[],cached:T[]):T[];

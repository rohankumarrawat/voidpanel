/**
 * VoidOnyx Tool Registry
 * ======================
 * Central registry of all available tools on the platform.
 * Adding a new tool = adding one entry here + creating the tool folder in client/src/tools/
 */
export interface ToolMeta {
    slug: string;
    name: string;
    description: string;
    category: string;
    icon: string;
    status: 'live' | 'beta' | 'coming-soon';
    path: string;
    apiPrefix?: string;
}
export declare const TOOLS_REGISTRY: ToolMeta[];
declare const router: import("express-serve-static-core").Router;
export default router;
//# sourceMappingURL=registry.d.ts.map
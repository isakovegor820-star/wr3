export interface Env {
  WR3_CORE_API_BASE: string;
}

const BLOCKED_PREFIXES = [
  "/v1/audits/",
  "/v1/disclosure-cases",
  "/v1/auth",
  "/v1/billing"
];

function isPrivatePath(pathname: string): boolean {
  if (pathname.includes("/raw-outputs") || pathname.includes("/findings")) {
    return true;
  }
  return BLOCKED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (isPrivatePath(url.pathname)) {
      return new Response(
        JSON.stringify({
          error: "private_api_must_use_core_api",
          reason: "edge_worker_does_not_proxy_private_findings_reports_or_billing"
        }),
        {
          status: 403,
          headers: { "content-type": "application/json" }
        }
      );
    }

    const upstream = new URL(url.pathname + url.search, env.WR3_CORE_API_BASE);
    return fetch(new Request(upstream, request));
  }
};

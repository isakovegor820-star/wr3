const API_BASE =
  process.env.WR3_SERVER_API_BASE_URL ??
  process.env.API_INTERNAL_BASE_URL ??
  "http://127.0.0.1:8001";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxyWr3Api(request: Request, context: RouteContext) {
  const { path } = await context.params;
  const incomingUrl = new URL(request.url);
  const upstreamUrl = new URL(`/${path.join("/")}${incomingUrl.search}`, API_BASE);
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual"
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = await request.arrayBuffer();
  }

  const upstream = await fetch(upstreamUrl, init);
  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders
  });
}

export const GET = proxyWr3Api;
export const POST = proxyWr3Api;
export const PUT = proxyWr3Api;
export const PATCH = proxyWr3Api;
export const DELETE = proxyWr3Api;
export const OPTIONS = proxyWr3Api;

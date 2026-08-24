interface StalenessResult {
  city_id?: string;
  feed?: string;
  stale?: boolean;
  error?: string | null;
}

interface StalenessPayload {
  event?: string;
  stale_feeds?: StalenessResult[];
  count?: number;
}

function json(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return json({ status: "healthy", service: "urban-signal-webhook-receiver" });
    }

    if (request.method !== "POST" || url.pathname !== "/feed-staleness") {
      return json({ detail: "Not found" }, 404);
    }

    let payload: unknown;
    try {
      payload = await request.json();
    } catch {
      return json({ detail: "Request body must be valid JSON" }, 400);
    }

    const results = Array.isArray(payload)
      ? payload as StalenessResult[]
      : payload && typeof payload === "object" && Array.isArray((payload as StalenessPayload).stale_feeds)
        ? (payload as StalenessPayload).stale_feeds ?? []
        : null;

    if (!results) {
      return json({ detail: "Expected a feed-staleness result array or payload" }, 422);
    }
    const stale = results.filter((result) => result.stale === true);
    const errors = results.filter((result) => Boolean(result.error));
    const receivedAt = new Date().toISOString();

    console.log(JSON.stringify({
      event: "feed_staleness_webhook",
      received_at: receivedAt,
      result_count: results.length,
      stale_count: stale.length,
      error_count: errors.length,
      stale_feeds: stale.map((result) => `${result.city_id ?? "unknown"}:${result.feed ?? "unknown"}`),
      error_feeds: errors.map((result) => `${result.city_id ?? "unknown"}:${result.feed ?? "unknown"}`),
    }));

    return json({
      accepted: true,
      received_at: receivedAt,
      result_count: results.length,
      stale_count: stale.length,
      error_count: errors.length,
    }, 202);
  },
};

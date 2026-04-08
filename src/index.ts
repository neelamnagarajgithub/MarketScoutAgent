// Cloudflare Workers - API Gateway/Proxy to Render Backend
interface CloudflareEnv {
  BACKEND_URL: string;
  CACHE: KVNamespace;
}

export default {
  async fetch(request: Request, env: CloudflareEnv): Promise<Response> {
    const url = new URL(request.url);
    
    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Max-Age': '3600',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      // Rate limiting via KV
      const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
      const rateLimitKey = `ratelimit:${clientIP}`;
      const currentCount = await env.CACHE.get(rateLimitKey);
      const count = currentCount ? parseInt(currentCount) + 1 : 1;

      if (count > 100) { // 100 requests per minute
        return new Response(JSON.stringify({ error: 'Rate limit exceeded' }), { 
          status: 429, 
          headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
        });
      }

      await env.CACHE.put(rateLimitKey, count.toString(), { expirationTtl: 60 });

      // Cache GET requests
      if (request.method === 'GET') {
        const cacheKey = `cache:${url.pathname}${url.search}`;
        const cached = await env.CACHE.get(cacheKey);
        
        if (cached) {
          return new Response(cached, {
            headers: { ...corsHeaders, 'X-Cache': 'HIT', 'Content-Type': 'application/json' },
          });
        }
      }

      // Proxy request to Render backend
      const backendUrl = `${env.BACKEND_URL}${url.pathname}${url.search}`;
      const backendRequest = new Request(backendUrl, {
        method: request.method,
        headers: new Headers(request.headers),
        body: request.method !== 'GET' ? request.body : undefined,
      });

      // Add trace headers
      backendRequest.headers.set('X-Forwarded-For', clientIP);
      backendRequest.headers.set('X-Forwarded-Proto', 'https');
      backendRequest.headers.delete('host');

      const response = await fetch(backendRequest);
      const responseBody = await response.text();

      // Cache GET responses
      if (request.method === 'GET' && response.ok) {
        const cacheKey = `cache:${url.pathname}${url.search}`;
        await env.CACHE.put(cacheKey, responseBody, { expirationTtl: 3600 }); // 1 hour
      }

      return new Response(responseBody, {
        status: response.status,
        headers: { ...Object.fromEntries(response.headers), ...corsHeaders },
      });
    } catch (error) {
      console.error('Worker error:', error);
      return new Response(JSON.stringify({ error: 'Internal Server Error', details: String(error) }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
  },

  // Scheduled cron job for health checks
  async scheduled(event: ScheduledEvent, env: CloudflareEnv): Promise<void> {
    try {
      const response = await fetch(`${env.BACKEND_URL}/health`);
      console.log('Health check completed:', response.status);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  },
};

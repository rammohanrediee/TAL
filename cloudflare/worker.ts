import { DurableObject } from "cloudflare:workers";

const PORT = 8000;
const INACTIVITY_TIMEOUT_MS = 2 * 60 * 1000;

const REQUIRED_SETTINGS = [
  "DATABASE_URL",
  "JWT_SECRET_KEY",
  "R2_ACCOUNT_ID",
  "R2_ACCESS_KEY_ID",
  "R2_SECRET_ACCESS_KEY",
  "R2_BUCKET_NAME",
  "R2_ENDPOINT_URL",
  "OAUTH_STATE_SECRET",
] as const;

type RequiredSetting = (typeof REQUIRED_SETTINGS)[number];

interface Env extends Record<RequiredSetting, string> {
  TAL_CONTAINER: DurableObjectNamespace<TalContainer>;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
  GOOGLE_REDIRECT_URI?: string;
  FRONTEND_URL?: string;
}

export class TalContainer extends DurableObject<Env> {
  private starting?: Promise<void>;

  async fetch(request: Request): Promise<Response> {
    this.starting ??= this.startAndWaitForHealth().finally(() => {
      this.starting = undefined;
    });
    await this.starting;

    const url = new URL(request.url);
    url.protocol = "http:";
    url.host = "container";
    const forwarded = new Request(url, request);
    forwarded.headers.delete("host");
    return this.ctx.container!.getTcpPort(PORT).fetch(forwarded);
  }

  private async startAndWaitForHealth(): Promise<void> {
    const container = this.ctx.container!;
    if (!container.running) {
      container.start({
        image: container.images.base,
        instance: "lite",
        enableInternet: true,
        env: {
          APP_ENV: "production",
          APP_DEBUG: "false",
          ...Object.fromEntries(
            REQUIRED_SETTINGS.map((name) => [name, this.env[name]]),
          ),
          ...(this.env.GOOGLE_CLIENT_ID && { GOOGLE_CLIENT_ID: this.env.GOOGLE_CLIENT_ID }),
          ...(this.env.GOOGLE_CLIENT_SECRET && { GOOGLE_CLIENT_SECRET: this.env.GOOGLE_CLIENT_SECRET }),
          ...(this.env.GOOGLE_REDIRECT_URI && { GOOGLE_REDIRECT_URI: this.env.GOOGLE_REDIRECT_URI }),
          ...(this.env.FRONTEND_URL && { FRONTEND_URL: this.env.FRONTEND_URL }),
        },
      });
    }

    await container.setInactivityTimeout(INACTIVITY_TIMEOUT_MS);
    const port = container.getTcpPort(PORT);
    for (let attempt = 0; attempt < 100; attempt++) {
      try {
        const response = await port.fetch("http://container/api/v1/health", {
          signal: AbortSignal.timeout(1000),
        });
        await response.body?.cancel();
        if (response.ok) return;
      } catch {
        // The HTTP server may still be starting.
      }
      await scheduler.wait(200);
    }
    throw new Error(`TAL container did not become healthy on port ${PORT}`);
  }
}

export default {
  fetch(request: Request, env: Env): Promise<Response> | Response {
    const missing = REQUIRED_SETTINGS.filter((name) => !env[name]);
    if (missing.length > 0) {
      console.error(`Missing Worker settings: ${missing.join(", ")}`);
      return new Response("TAL backend is not configured yet", {
        status: 503,
      });
    }
    return env.TAL_CONTAINER.getByName("tal-api").fetch(request);
  },
} satisfies ExportedHandler<Env>;

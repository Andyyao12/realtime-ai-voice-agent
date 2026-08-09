import { NextResponse } from "next/server";

import {
  createConnectionDetails,
  TokenRequestError,
  validateTokenRequest,
} from "@/lib/token";

export const runtime = "nodejs";

const NO_STORE = { "Cache-Control": "no-store, max-age=0" };

export async function POST(request: Request): Promise<NextResponse> {
  try {
    const text = await request.text();
    let body: unknown = undefined;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        throw new TokenRequestError(400, "INVALID_JSON", "Request body must contain valid JSON.");
      }
    }
    const details = await createConnectionDetails(validateTokenRequest(body));
    return NextResponse.json(details, { headers: NO_STORE });
  } catch (error) {
    if (error instanceof TokenRequestError) {
      return NextResponse.json(
        { error: { code: error.code, message: error.message } },
        { status: error.status, headers: NO_STORE },
      );
    }
    return NextResponse.json(
      { error: { code: "TOKEN_SERVICE_ERROR", message: "Unable to create a voice session." } },
      { status: 500, headers: NO_STORE },
    );
  }
}

import { NextRequest } from "next/server";
import { forward } from "@/lib/server-api";

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: Context): Promise<Response> {
  return forward(request, (await context.params).path, "GET");
}

export async function POST(request: NextRequest, context: Context): Promise<Response> {
  return forward(request, (await context.params).path, "POST");
}

import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { isSameOrigin } from "@/lib/request-origin";

describe("same-origin requests", () => {
  it("accepts the actual numeric loopback host despite NextURL normalization", () => {
    const request = new NextRequest("http://127.0.0.1:3024/api/session", { headers: { host:"127.0.0.1:3024", origin:"http://127.0.0.1:3024" } });
    expect(isSameOrigin(request)).toBe(true);
  });
  it("rejects other hosts, ports, protocols, null, and malformed origins", () => {
    for(const origin of ["https://attacker.invalid","http://localhost:3024","http://127.0.0.1:9999","https://127.0.0.1:3024","null","garbage"]){
      const request = new NextRequest("http://127.0.0.1:3024/api/session",{headers:{host:"127.0.0.1:3024",origin}});
      expect(isSameOrigin(request)).toBe(false);
    }
  });
  it("preserves origin-less server clients", () => {
    expect(isSameOrigin(new NextRequest("https://fraudlens.example/api/session",{headers:{host:"fraudlens.example"}}))).toBe(true);
  });
});

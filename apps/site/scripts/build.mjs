import { cp, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const dist = resolve(root, "dist");
await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await cp(resolve(root, "index.html"), resolve(dist, "index.html"));
await cp(resolve(root, "src"), resolve(dist, "src"), { recursive: true });
await cp(resolve(root, "public"), resolve(dist, "public"), { recursive: true });
for (const asset of ["facts.json", "llms.txt", "llms-full.txt", "robots.txt"]) {
  await cp(resolve(root, "public", asset), resolve(dist, asset));
}
await cp(resolve(root, "public", "_redirects"), resolve(dist, "_redirects"));
console.log("SITE_BUILD_OK");

import { readFile } from "node:fs/promises";

const html = await readFile(new URL("../apps/site/index.html", import.meta.url), "utf8");
const js = await readFile(new URL("../apps/site/src/main.js", import.meta.url), "utf8");
const requiredCities = [
  "New York City", "Chicago", "San Francisco Bay Area", "Seattle Metro",
  "Los Angeles Metro", "New Orleans Metro", "Norfolk", "Detroit", "Austin",
  "Cincinnati", "Boston", "Baltimore", "Montgomery County", "Baton Rouge", "Denver", "Philadelphia", "Washington DC"
];
for (const city of requiredCities) {
  if (!html.includes(city) && !js.includes(city)) throw new Error(`Missing city: ${city}`);
}
for (const phrase of ["architecture explorer", "municipal telemetry", "open the live dashboard", "coverage is not a marketing footnote", "6 months", "12 months", "18 months"]) {
  if (!html.toLowerCase().includes(phrase) && !js.toLowerCase().includes(phrase)) throw new Error(`Missing requirement: ${phrase}`);
}
console.log("SITE_CONTENT_OK");

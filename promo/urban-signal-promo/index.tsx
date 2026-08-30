/* @jsxImportSource @diffusionstudio/jsx */
/* Urban Signal — 20-second product promo.
 *
 * Presentation style: Vercel-style typographic punch on the Urban Signal
 * brand (ink canvas, lime signal accent, DM Sans + DM Mono).
 *
 * Beats:
 *   0.0–4.0   brand lockup + hex field
 *   4.0–8.0   the forecast promise
 *   8.0–12.0  the signal (101 metros · 4 feeds · 1 H3 grid)
 *  12.0–16.0  the pipeline (ingest → stream → grid → infer)
 *  16.0–20.0  call to action → live dashboard
 *
 * Usage:
 *   dapi open ~/Projects/urban-signal-promo
 *   dapi capture urban-signal-promo
 *   dapi check urban-signal-promo
 */

import { createMemo, type JSX as SolidJSX } from "solid-js";
import { useTicker, type Easing } from "@diffusionstudio/jsx";
import { clamp, easeOutCubic, fontMono, fontSans, lime, paper } from "./tokens";

const WIDTH = 1920;
const HEIGHT = 1080;
const DURATION = 20;

const SNAPPY_OUT = "cubicBezier(0,0.6,0.4,1)" satisfies Easing;
const EXPO_OUT = "cubicBezier(0,1,0,1)" satisfies Easing;
const IN_OUT = "cubicBezier(0.7,0,0.3,1)" satisfies Easing;

const muted = "#8fa093";
const ink = "#0c1514";

const HEX_TILE = `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="104"><path d="M60 2 112 30 112 74 60 102 8 74 8 30 Z" fill="none" stroke="rgba(197,243,106,0.14)" stroke-width="1"/></svg>`;
const HEX_BG = `url("data:image/svg+xml;utf8,${encodeURIComponent(HEX_TILE)}")`;

type RevealProps = {
  x: number;
  y: number;
  width: number;
  height: number;
  start: number;
  end: number;
  children: SolidJSX.Element;
  font: string;
  size: number;
  weight: number;
  color: string;
  align?: "left" | "center" | "right";
  baseline?: "top" | "middle" | "bottom";
  tracking?: number;
  rise?: number;
  slide?: number;
  delay?: number;
  inDur?: number;
  ease?: Easing;
  out?: boolean;
  outDur?: number;
};

function Reveal(props: RevealProps) {
  const localEnd = props.end - props.start;
  const delay = props.delay ?? 0;
  const inDur = props.inDur ?? 0.4;
  const ease = props.ease ?? SNAPPY_OUT;
  const outDur = props.outDur ?? 0.15;

  return (
    <text
      x={props.x}
      y={props.y}
      width={props.width}
      height={props.height}
      fontFamily={props.font}
      fontSize={props.size}
      fontWeight={props.weight}
      color={props.color}
      textAlign={props.align ?? "left"}
      textBaseline={props.baseline ?? "top"}
      letterSpacing={props.tracking ?? 0}
      start={props.start}
      end={props.end} id="qanzsm"
    >
      {props.children}
      <keyframeTrack property="opacity" id="ude9zz">
        <keyframe time={delay} value={0} id="twgut4" />
        <keyframe time={delay + inDur} value={1} easing={ease} id="to0g39" />
        {props.out ? <keyframe time={localEnd - outDur} value={1} id="gno5uo" /> : null}
        {props.out ? <keyframe time={localEnd} value={0} easing={ease} id="7idmfz" /> : null}
      </keyframeTrack>
      {props.rise ? (
        <keyframeTrack property="y" id="6fmpd9">
          <keyframe time={delay} value={props.y + props.rise} id="2zeeva" />
          <keyframe time={delay + inDur} value={props.y} easing={ease} id="wzrybf" />
        </keyframeTrack>
      ) : null}
      {props.slide ? (
        <keyframeTrack property="x" id="12qyl0">
          <keyframe time={delay} value={props.x + props.slide} id="4tl1f9" />
          <keyframe time={delay + inDur} value={props.x} easing={ease} id="oyd971" />
        </keyframeTrack>
      ) : null}
    </text>
  );
}

type DrawLineProps = {
  x: number;
  y: number;
  width: number;
  height: number;
  start: number;
  end: number;
  delay?: number;
  inDur?: number;
  ease?: Easing;
  fill?: string;
  out?: boolean;
};

function DrawLine(props: DrawLineProps) {
  const localEnd = props.end - props.start;
  const delay = props.delay ?? 0;
  const inDur = props.inDur ?? 0.45;
  const ease = props.ease ?? IN_OUT;

  return (
    <rect
      x={props.x}
      y={props.y}
      width={props.width}
      height={props.height}
      fill={props.fill ?? lime}
      start={props.start}
      end={props.end} id="w0l57v"
    >
      <keyframeTrack property="width" id="7zmzt6">
        <keyframe time={delay} value={0} id="g10rp5" />
        <keyframe time={delay + inDur} value={props.width} easing={ease} id="tapl7v" />
        {props.out ? <keyframe time={localEnd - 0.2} value={props.width} id="9vbs7g" /> : null}
        {props.out ? <keyframe time={localEnd} value={0} easing={ease} id="t1fyq1" /> : null}
      </keyframeTrack>
      <keyframeTrack property="opacity" id="l6ugvq">
        <keyframe time={delay} value={0} id="1wrm0d" />
        <keyframe time={delay + inDur} value={1} easing={ease} id="r1nn7s" />
        {props.out ? <keyframe time={localEnd - 0.2} value={1} id="2z6nyv" /> : null}
        {props.out ? <keyframe time={localEnd} value={0} easing={ease} id="e4qr8g" /> : null}
      </keyframeTrack>
    </rect>
  );
}

type CountUpProps = {
  target: number;
  x: number;
  y: number;
  width: number;
  height: number;
  start: number;
  end: number;
  delay?: number;
  dur?: number;
  size: number;
  color: string;
  font?: string;
};

function CountUp(props: CountUpProps) {
  const { time } = useTicker();
  const startAt = props.start + (props.delay ?? 0);
  const dur = props.dur ?? 1.1;

  const value = createMemo(() => {
    const local = (time() - startAt) / dur;
    return Math.round(props.target * easeOutCubic(clamp(local, 0, 1)));
  });

  return (
    <text
      x={props.x}
      y={props.y}
      width={props.width}
      height={props.height}
      fontFamily={props.font ?? fontMono}
      fontSize={props.size}
      fontWeight={700}
      color={props.color}
      textAlign="center"
      textBaseline="middle"
      start={props.start}
      end={props.end} id="7slu9q"
    >
      {value()}
      <keyframeTrack property="opacity" id="xb19ia">
        <keyframe time={props.delay ?? 0} value={0} id="7o390b" />
        <keyframe time={(props.delay ?? 0) + 0.3} value={1} easing={SNAPPY_OUT} id="lviqm4" />
      </keyframeTrack>
    </text>
  );
}

export default function Promo() {
  return (
    <stage background="#161616" camera={[0.3, 0, 0, 0.3, 85, 150]} id="o29zdb">
      <scene name="Urban Signal Promo" width={WIDTH} height={HEIGHT} fill={ink} active workarea={[0, DURATION]} id="k2ulfd">
        {/* Hex field — the H3 grid as a quiet texture for the whole cut */}
        <html x={0} y={0} width={WIDTH} height={HEIGHT} start={0} end={DURATION} id="2ycpod">
          <div style={`width:100%;height:100%;background-image:${HEX_BG};background-size:120px 104px;`} />
        </html>

        {/* ── Beat 1 · brand lockup (0.0–4.0) ─────────────────────────────── */}
        <sequence name="Beat 1 — brand" id="dp559y">
          <Reveal
            x={0} y={340} width={WIDTH} height={56} start={0} end={4}
            font={fontMono} size={38} weight={500} color={lime}
            align="center" tracking={10} delay={0.2} out
          >
            REAL-TIME SPATIAL INTELLIGENCE
          </Reveal>
          <DrawLine x={912} y={412} width={96} height={4} start={0} end={4} delay={0.45} out />
          <Reveal
            x={0} y={436} width={WIDTH} height={280} start={0} end={4}
            font={fontSans} size={190} weight={700} color={paper}
            align="center" baseline="middle" delay={0.5} inDur={0.5} rise={40} ease={EXPO_OUT} out
          >
            Urban Signal
          </Reveal>
          <Reveal
            x={0} y={742} width={WIDTH} height={48} start={0} end={4}
            font={fontMono} size={34} weight={400} color={muted}
            align="center" tracking={4} delay={0.9} out
          >
            COMMERCIAL CATALYST FORECASTING ENGINE
          </Reveal>
        </sequence>

        {/* ── Beat 2 · the forecast promise (4.0–8.0) ─────────────────────── */}
        <sequence name="Beat 2 — promise" id="juvzgl">
          <Reveal
            x={0} y={330} width={WIDTH} height={56} start={4} end={8}
            font={fontMono} size={38} weight={500} color={lime}
            align="center" tracking={10} delay={0.15} out
          >
            THE FORECAST
          </Reveal>
          <Reveal
            x={0} y={410} width={WIDTH} height={220} start={4} end={8}
            font={fontSans} size={168} weight={700} color={lime}
            align="center" baseline="middle" delay={0.4} inDur={0.5} rise={50} ease={EXPO_OUT} out
          >
            6–18 months
          </Reveal>
          <Reveal
            x={0} y={650} width={WIDTH} height={160} start={4} end={8}
            font={fontSans} size={96} weight={600} color={paper}
            align="center" baseline="middle" delay={0.7} inDur={0.5} rise={40} out
          >
            ahead of the market
          </Reveal>
          <Reveal
            x={0} y={820} width={WIDTH} height={48} start={4} end={8}
            font={fontMono} size={30} weight={400} color={muted}
            align="center" tracking={3} delay={1.0} out
          >
            APPRECIATION FORECASTS · LEADING MUNICIPAL SIGNALS
          </Reveal>
          {/* Pulse dot — signal indicator during the hold */}
          <rect x={953} y={280} width={14} height={14} cornerRadius={7} fill={lime} start={4} end={8} id="1yfj01">
            <keyframeTrack property="opacity" id="xvc2y1">
              <keyframe time={0.6} value={1} id="d5nkpk" />
              <keyframe time={1.0} value={0.35} easing="easeInOut" id="zgvn5j" />
              <keyframe time={1.4} value={1} easing="easeInOut" id="ooo8h0" />
              <keyframe time={3.6} value={1} id="n32fun" />
              <keyframe time={4} value={0} id="l36ae6" />
            </keyframeTrack>
          </rect>
        </sequence>

        {/* ── Beat 3 · the signal (8.0–12.0) ──────────────────────────────── */}
        <sequence name="Beat 3 — the signal" id="d6vfpo">
          <Reveal
            x={0} y={320} width={WIDTH} height={56} start={8} end={12}
            font={fontMono} size={38} weight={500} color={lime}
            align="center" tracking={10} delay={0.15} out
          >
            THE SIGNAL
          </Reveal>

          <CountUp target={101} x={180} y={430} width={600} height={240} start={8} end={12} delay={0.35} size={200} color={lime} />
          <CountUp target={4} x={660} y={430} width={600} height={240} start={8} end={12} delay={0.55} size={200} color={lime} />
          <CountUp target={1} x={1140} y={430} width={600} height={240} start={8} end={12} delay={0.75} size={200} color={lime} />

          <Reveal
            x={180} y={700} width={600} height={52} start={8} end={12}
            font={fontSans} size={44} weight={500} color={muted} align="center" delay={0.65} out
          >
            registered metros
          </Reveal>
          <Reveal
            x={660} y={700} width={600} height={52} start={8} end={12}
            font={fontSans} size={44} weight={500} color={muted} align="center" delay={0.85} out
          >
            municipal feeds
          </Reveal>
          <Reveal
            x={1140} y={700} width={600} height={52} start={8} end={12}
            font={fontSans} size={44} weight={500} color={muted} align="center" delay={1.05} out
          >
            multi-resolution H3 grid
          </Reveal>

          <Reveal
            x={0} y={830} width={WIDTH} height={48} start={8} end={12}
            font={fontMono} size={30} weight={400} color={muted}
            align="center" tracking={3} delay={1.3} out
          >
            PERMITS · 311 · LICENSES · DEEDS — RES 7/8/9
          </Reveal>
        </sequence>

        {/* ── Beat 4 · the pipeline (12.0–16.0) ───────────────────────────── */}
        <sequence name="Beat 4 — pipeline" id="62v1m5">
          <Reveal
            x={360} y={370} width={1200} height={56} start={12} end={16}
            font={fontMono} size={44} weight={500} color={paper}
            delay={0.25} slide={60} out
          >
            {"> ingest  permits · 311 · licenses · deeds"}
            <textRange start={0} end={1} color={lime} id="hdytj5" />
          </Reveal>
          <Reveal
            x={360} y={458} width={1200} height={56} start={12} end={16}
            font={fontMono} size={44} weight={500} color={paper}
            delay={0.55} slide={60} out
          >
            {"> stream  apache kafka"}
            <textRange start={0} end={1} color={lime} id="h17hz8" />
          </Reveal>
          <Reveal
            x={360} y={546} width={1200} height={56} start={12} end={16}
            font={fontMono} size={44} weight={500} color={paper}
            delay={0.85} slide={60} out
          >
            {"> grid    uber h3 · res 7–9"}
            <textRange start={0} end={1} color={lime} id="8ubd6i" />
          </Reveal>
          <Reveal
            x={360} y={634} width={1200} height={56} start={12} end={16}
            font={fontMono} size={44} weight={500} color={paper}
            delay={1.15} slide={60} out
          >
            {"> infer   onnx gpu · cuda fp16"}
            <textRange start={0} end={1} color={lime} id="cqnu5j" />
          </Reveal>
          <Reveal
            x={0} y={820} width={WIDTH} height={48} start={12} end={16}
            font={fontMono} size={30} weight={400} color={muted}
            align="center" tracking={3} delay={1.5} out
          >
            KAFKA EVENT STREAMS · UBER H3 · KUBERNETES · ONNX RUNTIME
          </Reveal>
        </sequence>

        {/* ── Beat 5 · call to action (16.0–20.0) ─────────────────────────── */}
        <sequence name="Beat 5 — CTA" id="hlnjsh">
          <Reveal
            x={0} y={360} width={WIDTH} height={56} start={16} end={20}
            font={fontMono} size={38} weight={500} color={lime}
            align="center" tracking={10} delay={0.15} out
          >
            LIVE NOW
          </Reveal>
          <Reveal
            x={0} y={430} width={WIDTH} height={200} start={16} end={20}
            font={fontSans} size={124} weight={700} color={paper}
            align="center" baseline="middle" delay={0.4} inDur={0.5} rise={50} ease={EXPO_OUT} out
          >
            Explore the live dashboard
          </Reveal>
          <Reveal
            x={0} y={680} width={WIDTH} height={64} start={16} end={20}
            font={fontMono} size={56} weight={600} color={lime}
            align="center" baseline="middle" tracking={2} delay={0.9} rise={24} out
          >
            us-dash.harlanljones.com
          </Reveal>
          <DrawLine x={840} y={760} width={240} height={4} start={16} end={20} delay={1.2} inDur={0.45} out />
        </sequence>

        {/* Fade to black to close the video */}
        <rect x={0} y={0} width={WIDTH} height={HEIGHT} fill="#000000" start={19.5} end={DURATION} id="fhrp76">
          <keyframeTrack property="opacity" id="u7uv0m">
            <keyframe time={0} value={0} id="ogea3w" />
            <keyframe time={0.5} value={1} easing={SNAPPY_OUT} id="8m0eu3" />
          </keyframeTrack>
        </rect>
      </scene>
    </stage>
  );
}
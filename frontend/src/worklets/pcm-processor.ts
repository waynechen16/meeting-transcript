// Runs in AudioWorkletGlobalScope — no ES imports allowed here.
// Globals provided by AudioWorkletGlobalScope:
declare const sampleRate: number;
declare abstract class AudioWorkletProcessor {
  readonly port: MessagePort;
  abstract process(inputs: Float32Array[][], outputs: Float32Array[][], parameters: Record<string, Float32Array>): boolean;
}
declare function registerProcessor(
  name: string,
  ctor: new () => AudioWorkletProcessor,
): void;

const TARGET_SR = 16_000;
const CHUNK_SAMPLES = 1_600; // 100 ms @ 16 kHz

class PcmProcessor extends AudioWorkletProcessor {
  private readonly ratio: number;
  private readonly buf: Float32Array;
  private len = 0;
  private phase = 0;

  constructor() {
    super();
    this.ratio = sampleRate / TARGET_SR;
    this.buf = new Float32Array(CHUNK_SAMPLES);
  }

  process(inputs: Float32Array[][]): boolean {
    const ch0 = inputs[0]?.[0];
    if (!ch0?.length) return true;

    const ch1 = inputs[0][1];
    const inputLen = ch0.length;

    // Resample to TARGET_SR via linear interpolation, mix to mono
    while (this.phase < inputLen) {
      const i0 = Math.floor(this.phase);
      const i1 = Math.min(i0 + 1, inputLen - 1);
      const t = this.phase - i0;

      const s0 = ch1 ? (ch0[i0] + ch1[i0]) * 0.5 : ch0[i0];
      const s1 = ch1 ? (ch0[i1] + ch1[i1]) * 0.5 : ch0[i1];
      this.buf[this.len++] = s0 + (s1 - s0) * t;

      if (this.len >= CHUNK_SAMPLES) this.flush();

      this.phase += this.ratio;
    }
    this.phase -= inputLen;

    return true;
  }

  private flush(): void {
    const int16 = new Int16Array(this.len);
    for (let i = 0; i < this.len; i++) {
      const s = Math.max(-1, Math.min(1, this.buf[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    this.port.postMessage(int16.buffer, [int16.buffer]);
    this.len = 0;
  }
}

registerProcessor("pcm-processor", PcmProcessor);

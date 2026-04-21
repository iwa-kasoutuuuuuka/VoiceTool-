#include <stdio.h>
#include <float.h>
#include <math.h>

#if defined(_MSC_VER)
    #include <intrin.h>
    #define EXPORT __declspec(dllexport)
#else
    #include <x86intrin.h>
    #define EXPORT __attribute__((visibility("default")))
#endif

/**
 * 音声データからエンベロープ（各ピクセル範囲のMin/Max）を高速に抽出する。
 * 
 * @param data          入力音声データ (float配列)
 * @param total_samples 総サンプル数
 * @param width         ターゲットピクセル幅
 * @param out_min       結果の最小値配列 (長さ: width)
 * @param out_max       結果の最大値配列 (長さ: width)
 */
EXPORT void get_envelope(const float* data, size_t total_samples, int width, float* out_min, float* out_max) {
    if (width <= 0 || total_samples <= 0) return;

    size_t samples_per_pixel = total_samples / width;
    if (samples_per_pixel == 0) samples_per_pixel = 1;

    for (int x = 0; x < width; x++) {
        size_t start = x * samples_per_pixel;
        size_t end = (x + 1) * samples_per_pixel;
        if (end > total_samples) end = total_samples;

        float min_val = FLT_MAX;
        float max_val = -FLT_MAX;

        // SIMD化を見越したループ (SSE2/AVX等でさらに高速化可能)
        // ここではコンパイラの自動ベクトル化を期待した単純な実装にする
        for (size_t i = start; i < end; i++) {
            float v = data[i];
            if (!isfinite(v)) continue;
            if (v < min_val) min_val = v;
            if (v > max_val) max_val = v;
        }

        out_min[x] = (min_val == FLT_MAX) ? 0.0f : min_val;
        out_max[x] = (max_val == -FLT_MAX) ? 0.0f : max_val;
    }
}

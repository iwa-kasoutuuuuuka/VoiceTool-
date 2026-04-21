#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#if defined(_MSC_VER)
    #include <intrin.h>
    #define EXPORT __declspec(dllexport)
#else
    #include <x86intrin.h>
    #define EXPORT __attribute__((visibility("default")))
#endif

/**
 * ゲイン（音量）を適用する。
 * SIMD (SSE2/AVX2) による高速計算。
 * 
 * @param data       音声データ (float配列)
 * @param n          サンプル数
 * @param gain_raw   倍率 (dBではなく線形倍率)
 */
EXPORT void apply_gain(float* data, size_t n, float gain_raw) {
    if (data == NULL || n == 0 || gain_raw == 1.0f) return;
    if (!isfinite(gain_raw)) return;

    size_t i = 0;
    
    #if defined(__AVX2__)
    // AVX2: 一度に8個のfloatを処理
    __m256 vgain = _mm256_set1_ps(gain_raw);
    for (; i + 8 <= n; i += 8) {
        __m256 vdata = _mm256_loadu_ps(&data[i]);
        // NaN/Inf チェック（必要ならここでマスク可能だが、基本は一括処理）
        vdata = _mm256_mul_ps(vdata, vgain);
        _mm256_storeu_ps(&data[i], vdata);
    }
    #endif

    // 残りのサンプルをSSEまたはスカラで処理
    __m128 vgain128 = _mm_set1_ps(gain_raw);
    for (; i + 4 <= n; i += 4) {
        __m128 vdata = _mm_loadu_ps(&data[i]);
        vdata = _mm_mul_ps(vdata, vgain128);
        _mm_storeu_ps(&data[i], vdata);
    }

    for (; i < n; i++) {
        // 個別サンプルがNaNなら0にするガードを追加
        if (!isfinite(data[i])) {
            data[i] = 0.0f;
            continue;
        }
        data[i] *= gain_raw;
    }
}

/**
 * ハードクリッピング（リミッターの簡易版）
 * 設定値を超える振幅をカットし、デジタルノイズを防ぐ。
 */
EXPORT void apply_clipping(float* data, size_t n, float threshold) {
    if (n == 0) return;
    float neg_threshold = -threshold;

    for (size_t i = 0; i < n; i++) {
        if (data[i] > threshold) data[i] = threshold;
        else if (data[i] < neg_threshold) data[i] = neg_threshold;
    }
}

/**
 * 音声データの高速連結と無音挿入。
 * 
 * @param dst        出力先バッファ
 * @param src        コピー元バッファ
 * @param n          コピーするサンプル数
 */
EXPORT void copy_buffer(float* dst, const float* src, size_t n) {
    if (n > 0) {
        memcpy(dst, src, n * sizeof(float));
    }
}

EXPORT void fill_silence(float* dst, size_t n) {
    if (n > 0) {
        memset(dst, 0, n * sizeof(float));
    }
}

export function readableErrorMessage(error: unknown, fallback = 'Islem tamamlanamadi.'): string {
    const maybeError = error as {
        message?: string;
        response?: { data?: { detail?: unknown } };
    };
    const detail = maybeError?.response?.data?.detail;
    const message = typeof detail === 'string'
        ? detail
        : typeof detail === 'object' && detail && 'message' in detail
            ? String((detail as { message?: unknown }).message || '')
            : maybeError?.message;
    const raw = String(message || fallback).trim();
    const normalized = raw.toLowerCase();

    if (normalized.includes('model_dump') || normalized.includes("object has no attribute")) {
        return 'Analiz sonucu beklenen formata cevrilemedi. Backend yeniden baslatildiktan sonra tekrar deneyin.';
    }
    if (normalized.includes("coordinate 'lower' is less than 'upper'")) {
        return 'Screenshot koordinatlari beklenen sirada degil. Gorseli yeniden secip tekrar deneyin.';
    }
    if (normalized.includes('timeout') || normalized.includes('zaman as') || normalized.includes('zaman aş')) {
        return 'Islem zaman asimina ugradi. Hedef yavas yanit veriyor olabilir; tekrar deneyin.';
    }
    if (normalized.includes('network') || normalized.includes('failed to fetch')) {
        return 'Backend veya hedef servis yanit vermedi. Servislerin calistigini kontrol edip tekrar deneyin.';
    }
    if (!raw) {
        return fallback;
    }
    return raw.length > 180 ? `${raw.slice(0, 177)}...` : raw;
}

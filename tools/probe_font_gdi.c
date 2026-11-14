/* Offscreen GDI reference probe. Never loads or attaches to the game.
 *
 * Run only in a separate, disposable Wine prefix with a copied font file.
 * Input LOGFONTA bytes are an explicit hypothesis, not a live-client binding.
 * The graphics DLL's inspected path uses a memory DC, white text on black,
 * TA_LEFT|TA_TOP, MM_TEXT mapping, and one UTF-16 unit per ExtTextOutW call.
 * BkMode is left at its observed DC default. Reuse diagnostics retain the
 * DIB between glyphs, as the inspected client paths do (no explicit clear).
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_WIDTH = 128, MAX_HEIGHT = 96 };
static const WCHAR glyphs[] = { '/', 'l', 'o', 'c', 'a', 't', 'i', 'n', '|' };

static int put(HANDLE output, const void *bytes, DWORD count) {
    DWORD written = 0;
    return WriteFile(output, bytes, count, &written, NULL) && written == count;
}

int main(int argc, char **argv) {
    if (argc != 4 && argc != 5) {
        fprintf(stderr, "usage: probe_font_gdi.exe COPIED_FONT LOGFONT_60_BYTES NEW_OUTPUT [reuse|clear-each|white-reuse]\n");
        return 2;
    }
    uint32_t reset_mode = 1; /* Zero once, then reuse; never an implicit live claim. */
    if (argc == 5) {
        if (!strcmp(argv[4], "clear-each")) reset_mode = 0;
        else if (!strcmp(argv[4], "reuse")) reset_mode = 1;
        else if (!strcmp(argv[4], "white-reuse")) reset_mode = 2;
        else { fprintf(stderr, "Unknown DIB reset mode\n"); return 2; }
    }
    int status = 1, registered = 0;
    HDC dc = NULL;
    HFONT font = NULL;
    HBITMAP bitmap = NULL;
    HGDIOBJ old_font = NULL, old_bitmap = NULL;
    HANDLE output = INVALID_HANDLE_VALUE;
    unsigned char *selected_font = NULL;
    LOGFONTA descriptor;
    FILE *input = fopen(argv[2], "rb");
    if (!input) { fprintf(stderr, "Cannot open descriptor\n"); goto done; }
    size_t count = fread(&descriptor, 1, sizeof descriptor, input);
    int extra = fgetc(input);
    fclose(input);
    if (sizeof descriptor != 60 || count != 60 || extra != EOF ||
        descriptor.lfHeight <= 0 || descriptor.lfHeight > 64 ||
        descriptor.lfWidth != 0 || descriptor.lfEscapement != 0 || descriptor.lfOrientation != 0 ||
        descriptor.lfWeight < 0 || descriptor.lfWeight > 1000 ||
        !descriptor.lfFaceName[0] || !memchr(descriptor.lfFaceName, 0, LF_FACESIZE)) {
        fprintf(stderr, "Unsupported or malformed LOGFONTA hypothesis\n"); goto done;
    }
    registered = AddFontResourceExA(argv[1], FR_PRIVATE, NULL);
    if (!registered) { fprintf(stderr, "Copied font registration failed\n"); goto done; }
    dc = CreateCompatibleDC(NULL);
    font = CreateFontIndirectA(&descriptor);
    if (!dc || !font) { fprintf(stderr, "Memory font/DC creation failed\n"); goto done; }
    old_font = SelectObject(dc, font);
    if (!old_font || old_font == HGDI_ERROR) { fprintf(stderr, "Font selection failed\n"); goto done; }
    TEXTMETRICA metrics;
    char face[128] = {0};
    if (!GetTextMetricsA(dc, &metrics) || !GetTextFaceA(dc, sizeof face, face)) {
        fprintf(stderr, "Selected-font metrics unavailable\n"); goto done;
    }
    if (metrics.tmMaxCharWidth <= 0 || metrics.tmMaxCharWidth > MAX_WIDTH ||
        metrics.tmHeight <= 0 || metrics.tmHeight > MAX_HEIGHT) {
        fprintf(stderr, "Selected-font bitmap exceeds probe bounds\n"); goto done;
    }
    int width = metrics.tmMaxCharWidth, height = metrics.tmHeight;
    /* Retain actual selected font bytes. The host must compare their hash
     * with the supplied copied font, rather than trusting a family name. */
    DWORD font_size = GetFontData(dc, 0, 0, NULL, 0);
    if (font_size == GDI_ERROR || !font_size || font_size > 32 * 1024 * 1024) {
        fprintf(stderr, "Selected-font identity unavailable\n"); goto done;
    }
    selected_font = malloc(font_size);
    if (!selected_font || GetFontData(dc, 0, 0, selected_font, font_size) != font_size) {
        fprintf(stderr, "Selected-font read failed\n"); goto done;
    }
    BITMAPINFO info;
    memset(&info, 0, sizeof info);
    info.bmiHeader.biSize = sizeof info.bmiHeader;
    info.bmiHeader.biWidth = width;
    info.bmiHeader.biHeight = -height;
    info.bmiHeader.biPlanes = 1;
    info.bmiHeader.biBitCount = 32;
    info.bmiHeader.biCompression = BI_RGB;
    void *pixels = NULL;
    bitmap = CreateDIBSection(dc, &info, DIB_RGB_COLORS, &pixels, NULL, 0);
    if (!bitmap || !pixels) { fprintf(stderr, "Memory bitmap creation failed\n"); goto done; }
    old_bitmap = SelectObject(dc, bitmap);
    if (!old_bitmap || old_bitmap == HGDI_ERROR) { fprintf(stderr, "Bitmap selection failed\n"); goto done; }
    if (!SetMapMode(dc, MM_TEXT) || SetBkColor(dc, 0) == CLR_INVALID ||
        SetTextColor(dc, 0xffffff) == CLR_INVALID || SetTextAlign(dc, 0) == GDI_ERROR) {
        fprintf(stderr, "Memory text state failed\n"); goto done;
    }
    int mapping_mode = GetMapMode(dc), background_mode = GetBkMode(dc);
    if (mapping_mode != MM_TEXT || (background_mode != OPAQUE && background_mode != TRANSPARENT)) {
        fprintf(stderr, "Memory DC state query failed\n"); goto done;
    }
    output = CreateFileA(argv[3], GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
    if (output == INVALID_HANDLE_VALUE) { fprintf(stderr, "New output path required\n"); goto done; }
    const char magic[8] = {'E','Q','L','G','D','I','2',0};
    uint32_t header[] = {2, width, height, sizeof glyphs / sizeof glyphs[0], font_size,
        reset_mode, mapping_mode, background_mode};
    int32_t values[] = {metrics.tmHeight, metrics.tmAscent, metrics.tmDescent,
        metrics.tmInternalLeading, metrics.tmExternalLeading, metrics.tmAveCharWidth,
        metrics.tmMaxCharWidth, metrics.tmWeight, metrics.tmOverhang,
        metrics.tmDigitizedAspectX, metrics.tmDigitizedAspectY};
    if (!put(output, magic, sizeof magic) || !put(output, header, sizeof header) ||
        !put(output, &descriptor, sizeof descriptor) || !put(output, values, sizeof values) ||
        !put(output, face, sizeof face) || !put(output, selected_font, font_size)) {
        fprintf(stderr, "Header write failed\n"); goto done;
    }
    memset(pixels, reset_mode == 2 ? 255 : 0, width * height * 4);
    for (unsigned int i = 0; i < sizeof glyphs / sizeof glyphs[0]; ++i) {
        SIZE extent;
        if (reset_mode == 0) memset(pixels, 0, width * height * 4);
        if (!GetTextExtentPoint32W(dc, glyphs + i, 1, &extent) ||
            extent.cx <= 0 || extent.cx > width || extent.cy <= 0 || extent.cy > height ||
            !GdiFlush() || !ExtTextOutW(dc, 0, 0, ETO_OPAQUE, NULL, glyphs + i, 1, NULL) || !GdiFlush()) {
            fprintf(stderr, "Bounded single-glyph raster failed\n"); goto done;
        }
        int32_t fields[] = {glyphs[i], extent.cx, extent.cy};
        if (!put(output, fields, sizeof fields) || !put(output, pixels, width * height * 4)) {
            fprintf(stderr, "Glyph write failed\n"); goto done;
        }
    }
    status = 0;
done:
    if (output != INVALID_HANDLE_VALUE) CloseHandle(output);
    if (dc && old_bitmap && old_bitmap != HGDI_ERROR) SelectObject(dc, old_bitmap);
    if (dc && old_font && old_font != HGDI_ERROR) SelectObject(dc, old_font);
    if (bitmap) DeleteObject(bitmap);
    if (font) DeleteObject(font);
    if (dc) DeleteDC(dc);
    if (registered) RemoveFontResourceExA(argv[1], FR_PRIVATE, NULL);
    free(selected_font);
    return status;
}

# Dataset reconciliation

Page checked: 2026-11-16<br>
Source: <https://www.kaggle.com/datasets/danielgrijalvas/movies><br>
Kaggle page version: 2<br>
Page metadata modified: 2021-07-23T19:48:26.173Z

| item | dataset_lokal | metadata_kaggle | penilaian |
| --- | --- | --- | --- |
| Nama file lokal | movies.csv | movies.csv pada salinan lokal | Diperiksa |
| Revisi lokal | Tidak tercatat | Kaggle versi 2 | Identitas revisi lokal tidak diketahui |
| Tanggal pemeriksaan halaman | 2026-11-16 | Tanggal pemeriksaan halaman Kaggle saat audit | Bukan tanggal unduh historis |
| Tanggal modifikasi halaman | 2021-07-23T19:48:26.173Z | Metadata halaman Kaggle | Tersedia |
| Baris data | 7668 | 6820 | Berbeda dari deskripsi halaman |
| Kolom | 15 | 15 | Jumlah sesuai |
| Nama kolom | name; rating; genre; year; released; score; votes; director; writer; star; country; budget; gross; company; runtime | budget; company; country; director; genre; gross; name; rating; released; runtime; score; star; votes; writer; year | Sama (urutan diabaikan) |
| Rentang tahun | 1980–2020 | 1986–2016 | Berbeda dari deskripsi halaman |
| Identitas file biner | addcc5390a8ebca83ff24f8b8de9341ca21ed8572931fd0a055b7c212d21e142 | Tidak tersedia untuk pembandingan arsip | Belum terverifikasi |

## Assessment

The local CSV contains 7,668 data rows, 15 columns, and year values from 1980 to 2020. The Kaggle page description reports 6,820 movies from 1986 to 2016. The 15 field names match, but the row count and year range in the page description do not match the local file.

The Kaggle page identifies version 2; it does not establish which version produced this local copy. The public version-2 download endpoint returned HTTP 404 during this check, so an exact content or binary comparison was not possible. The Kaggle description may be stale; the evidence is insufficient to distinguish stale metadata from a different local revision. The local SHA-256 is recorded in `dataset_reconciliation.json` to identify this exact file.

The page-check date above is the date of this metadata inspection, **not** a historical download date. The local file revision and historical download date were not supplied. The filesystem modification time is recorded as file-system metadata only and must not be interpreted as the dataset's creation or download date.

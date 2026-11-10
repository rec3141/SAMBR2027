<?php
// SAMBR2027 portal: receive "report incorrect data" submissions.
// Appends one JSON line per report to ~/sambr2027_reports/reports.jsonl (outside the web root).
// Optional e-mail notification: put an address in ~/sambr2027_reports/notify_to (not in the repo).
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function out($code, $arr) { http_response_code($code); echo json_encode($arr); exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(405, ['ok' => false, 'error' => 'POST only']);

$raw = file_get_contents('php://input', false, null, 0, 20000);
$in = json_decode($raw, true);
if (!is_array($in)) out(400, ['ok' => false, 'error' => 'bad request']);
if (!empty($in['website'])) out(200, ['ok' => true]);  // honeypot: silently drop bots

$TYPES = ['location', 'lme', 'fec', 'obs_span', 'metadata', 'missing_paper', 'other'];
$clean = function ($v, $n) { return mb_substr(trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', (string)$v)), 0, $n); };

$rep = [
  'time'     => gmdate('c'),
  'citekey'  => $clean($in['citekey'] ?? '', 60),
  'type'     => in_array($in['type'] ?? '', $TYPES, true) ? $in['type'] : 'other',
  'details'  => $clean($in['details'] ?? '', 4000),
  'name'     => $clean($in['name'] ?? '', 120),
  'email'    => $clean($in['email'] ?? '', 160),
  'context'  => $clean($in['context'] ?? '', 600),
  'page'     => $clean($_SERVER['HTTP_REFERER'] ?? '', 300),
  'ip_hash'  => substr(hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . 'sambr2027'), 0, 16),
];
if ($rep['details'] === '' || mb_strlen($rep['details']) < 3) out(400, ['ok' => false, 'error' => 'Please describe the problem.']);
if ($rep['citekey'] !== '' && !preg_match('/^[A-Za-z0-9_.-]+$/', $rep['citekey'])) out(400, ['ok' => false, 'error' => 'bad citekey']);

$dir = dirname(__DIR__, 2) . '/sambr2027_reports';
if (!is_dir($dir) && !mkdir($dir, 0700, true)) out(500, ['ok' => false, 'error' => 'storage unavailable']);

// throttle: max 20 reports per IP per hour
$tf = "$dir/throttle.json";
$fh = fopen($tf, 'c+');
if ($fh && flock($fh, LOCK_EX)) {
  $t = json_decode(stream_get_contents($fh) ?: '{}', true) ?: [];
  $now = time();
  foreach ($t as $k => $ts) { $t[$k] = array_values(array_filter($ts, fn($x) => $x > $now - 3600)); if (!$t[$k]) unset($t[$k]); }
  $mine = $t[$rep['ip_hash']] ?? [];
  if (count($mine) >= 20) { flock($fh, LOCK_UN); fclose($fh); out(429, ['ok' => false, 'error' => 'Too many reports; please try again later.']); }
  $mine[] = $now; $t[$rep['ip_hash']] = $mine;
  ftruncate($fh, 0); rewind($fh); fwrite($fh, json_encode($t)); flock($fh, LOCK_UN); fclose($fh);
}

$line = json_encode($rep, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . "\n";
if (file_put_contents("$dir/reports.jsonl", $line, FILE_APPEND | LOCK_EX) === false) out(500, ['ok' => false, 'error' => 'could not save']);

$nt = "$dir/notify_to";
if (is_readable($nt)) {
  $to = trim(file_get_contents($nt));
  if (filter_var($to, FILTER_VALIDATE_EMAIL)) {
    $subj = 'SAMBR2027 data report: ' . ($rep['citekey'] ?: 'general') . ' (' . $rep['type'] . ')';
    $body = "Citekey: {$rep['citekey']}\nType: {$rep['type']}\nFrom: {$rep['name']} {$rep['email']}\nContext: {$rep['context']}\n\n{$rep['details']}\n\n{$rep['time']}\n";
    @mail($to, $subj, $body, "From: SAMBR2027 portal <noreply@cryomics.org>\r\nContent-Type: text/plain; charset=utf-8");
  }
}
out(200, ['ok' => true]);

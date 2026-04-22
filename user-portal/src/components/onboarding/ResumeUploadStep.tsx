import { useRef, useState } from 'react';

import { api, ApiError } from '../../lib/api';
import { GradientButton } from '../ui/GradientButton';

type Props = {
  onAdvance: () => void;
};

const DROPZONE_BACKGROUND = {
  background:
    'linear-gradient(#fff,#fff) padding-box, repeating-linear-gradient(135deg, #e8e6e1 0 6px, transparent 6px 12px) border-box',
  border: '1.5px dashed transparent',
};

const DROPZONE_BACKGROUND_HOVER = {
  background:
    'linear-gradient(#faf9f6,#faf9f6) padding-box, repeating-linear-gradient(135deg, #c9c6be 0 6px, transparent 6px 12px) border-box',
  border: '1.5px dashed transparent',
};

function UploadIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
      <path d="M12 18v-6" />
      <path d="m9 15 3-3 3 3" />
    </svg>
  );
}

export function ResumeUploadStep({ onAdvance }: Props) {
  const [pasteMode, setPasteMode] = useState(false);
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [hover, setHover] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      await api.profile.uploadResume(form);
      onAdvance();
    } catch (caught) {
      const message =
        caught instanceof ApiError ? caught.message : (caught as Error).message;
      setError(message);
      setPasteMode(true);
    } finally {
      setBusy(false);
    }
  }

  async function onPaste() {
    setBusy(true);
    setError(null);
    try {
      await api.profile.uploadResumeText(text);
      onAdvance();
    } catch (caught) {
      const message =
        caught instanceof ApiError ? caught.message : (caught as Error).message;
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
      <div className="lg:col-span-7">
        <div className="text-xs uppercase tracking-[0.18em] text-ink-3">
          First, the easy part
        </div>
        <h1 className="mt-3 text-[46px] font-semibold leading-[1.02] tracking-[-0.02em] text-ink">
          Hand us your
          <br />
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            resume
          </span>
          <span> — that's it.</span>
        </h1>
        <p className="mt-4 max-w-md text-[15px] leading-relaxed text-ink-3">
          We'll use it to judge roles against your actual experience, not
          keywords. You can update it anytime from Settings.
        </p>

        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
          onFocus={() => setHover(true)}
          onBlur={() => setHover(false)}
          style={hover ? DROPZONE_BACKGROUND_HOVER : DROPZONE_BACKGROUND}
          className="mt-8 w-full rounded-3xl p-10 text-left transition-colors duration-150 motion-reduce:transition-none focus:outline-none focus-visible:ring-2 focus-visible:ring-ink/10"
          aria-label="Upload resume — drop or browse"
          disabled={busy}
        >
          <div className="flex items-start gap-5">
            <span className="flex h-12 w-12 flex-none items-center justify-center rounded-xl border border-line bg-white text-ink-2">
              <UploadIcon />
            </span>
            <div>
              <div className="text-[15px] font-medium text-ink">
                Drop your resume here, or click to browse
              </div>
              <div className="mt-1 text-[13px] text-ink-3">
                PDF or DOCX · up to 10 MB · parsed on device first
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {['resume.pdf', 'cv_final_v3.docx', 'example filenames'].map(
                  (sample) => (
                    <span
                      key={sample}
                      className="rounded-full border border-line bg-white px-3 py-1 text-[12px] text-ink-3"
                    >
                      {sample}
                    </span>
                  ),
                )}
              </div>
            </div>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void onFile(file);
            }}
          />
        </button>

        <div className="mt-5">
          <button
            type="button"
            onClick={() => setPasteMode((previous) => !previous)}
            className="text-[13px] text-ink-3 underline decoration-dotted underline-offset-4 hover:text-ink-2"
          >
            {pasteMode ? 'Upload a file instead' : 'Paste plain text instead'}
          </button>
        </div>

        {pasteMode && (
          <div className="mt-4 flex flex-col gap-3">
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={10}
              className="w-full rounded-2xl border border-line-2 bg-white p-4 font-mono text-[13px] leading-relaxed text-ink focus:border-ink focus:outline-none focus:ring-4 focus:ring-black/5"
              placeholder="Paste your resume as plain text or markdown…"
            />
            <GradientButton
              disabled={busy || !text.trim()}
              onClick={() => void onPaste()}
              shape="pill"
              className="self-start"
            >
              {busy ? 'Processing…' : 'Continue'}
            </GradientButton>
          </div>
        )}

        {error && (
          <p
            role="alert"
            className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800"
          >
            {error}
          </p>
        )}
      </div>

      <aside className="lg:col-span-5">
        <div className="rounded-3xl border border-[#ece9e2] bg-white p-6 shadow-[0_1px_0_rgba(31,29,26,0.02),0_24px_48px_-28px_rgba(31,29,26,0.18)]">
          <div className="text-xs uppercase tracking-[0.18em] text-ink-3">
            What happens with it
          </div>
          <ul className="mt-4 space-y-3 text-[14px] leading-relaxed text-ink-2">
            {[
              'Parsed into a private profile — companies, titles, dates, skills.',
              'Used as the ground truth when we evaluate jobs.',
              'Never shown to employers. Never sold. Delete it with one click.',
            ].map((bullet) => (
              <li key={bullet} className="flex gap-3">
                <span className="mt-[0.55em] block h-1.5 w-1.5 flex-none rounded-full bg-ink" />
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
          <div className="my-5 border-t border-line" />
          <p className="text-[12px] text-ink-3">
            Takes ~20 seconds. You can tweak the extracted profile before
            continuing.
          </p>
        </div>

        <div
          aria-hidden
          className="mt-5 rounded-3xl border border-dashed border-line-2 bg-transparent p-6"
        >
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink-4">
            Preview · will populate
          </div>
          <div className="mt-4 space-y-3">
            <div className="h-3 w-3/5 rounded-full bg-line" />
            <div className="h-3 w-4/5 rounded-full bg-line" />
            <div className="h-3 w-2/5 rounded-full bg-line" />
          </div>
        </div>
      </aside>
    </div>
  );
}

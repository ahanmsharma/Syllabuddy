import React, { useEffect, useRef, useState } from "react";

type Props = {
  segments: string[];               // len = n_blanks + 1
  answers: string[];                // correct tokens per blank
  initialBank: string[];            // scrambled bank
  initialFills: (string | null)[];  // current fills
  showFeedback: boolean;            // add correct/wrong classes
  pageFrame?: "none" | "good" | "mixed"; // optional page-wide border
  badPct?: number;                  // % red for mixed
};

const DndCloze: React.FC<Props> = ({
  segments, answers, initialBank, initialFills, showFeedback, pageFrame = "none", badPct = 30
}) => {
  const nBlanks = answers.length;
  const [bank, setBank] = useState<string[]>(initialBank);
  const [fills, setFills] = useState<(string | null)[]>(initialFills);
  const dragging = useRef<string | null>(null);

  useEffect(() => { setBank(initialBank); }, [initialBank.join("|")]);
  useEffect(() => { setFills(initialFills); }, [initialFills.join("|")]);

  const onDragStartChip = (token: string) => (e: React.DragEvent) => {
    dragging.current = token;
    e.dataTransfer.setData("text/plain", token);
    e.dataTransfer.effectAllowed = "move";
  };
  const onDragOver = (e: React.DragEvent) => e.preventDefault();

  const onDropBank = (e: React.DragEvent) => {
    e.preventDefault();
    const tok = e.dataTransfer.getData("text/plain");
    if (!tok) return;
    const idx = fills.findIndex(f => f === tok);
    if (idx >= 0) {
      const nf = fills.slice();
      nf[idx] = null;
      setFills(nf);
      setBank(prev => [...prev, tok]);
    }
    dragging.current = null;
  };
  const onDropBlank = (i: number) => (e: React.DragEvent) => {
    e.preventDefault();
    const tok = e.dataTransfer.getData("text/plain");
    if (!tok) return;
    const inBank = bank.includes(tok);
    const fromIdx = fills.findIndex(f => f === tok);

    const nf = fills.slice();
    if (fromIdx >= 0) nf[fromIdx] = null;
    if (inBank) setBank(prev => prev.filter(t => t !== tok));
    if (nf[i]) setBank(prev => [...prev, nf[i] as string]);
    nf[i] = tok;
    setFills(nf);
    dragging.current = null;
  };

  const blankClass = (i: number) => {
    const base = ["blank"];
    if (fills[i]) base.push("filled");
    if (showFeedback && fills[i]) {
      const ok = fills[i]!.trim().toLowerCase() === answers[i].trim().toLowerCase();
      base.push(ok ? "correct" : "wrong");
    }
    return base.join(" ");
  };

  // expose state to Streamlit wrapper
  (window as any).__DND_CLOZE_STATE__ = { bank, fills };

  // optional page-wide frame (inserted here so it renders inside the iframe)
  const frame =
    pageFrame === "none" ? null :
    <div className={`page-frame ${pageFrame}`} style={{"--badpct": `${badPct}%`} as React.CSSProperties} />;

  return (
    <div className="wrap">
      {frame}
      <div className="bank" onDrop={onDropBank} onDragOver={onDragOver}>
        {bank.map((tok, idx) => (
          <div
            key={tok + idx}
            className="chip"
            draggable
            onDragStart={onDragStartChip(tok)}
            title="Drag into a blank"
          >
            {tok}
          </div>
        ))}
      </div>

      <div className="row">
        {Array.from({ length: nBlanks }).map((_, i) => (
          <React.Fragment key={`seg-${i}`}>
            <span className="seg">{segments[i]}</span>
            <span
              className={blankClass(i)}
              onDrop={onDropBlank(i)}
              onDragOver={onDragOver}
              title={fills[i] ? "Drag back to the bank to remove" : "Drop a word here"}
            >
              {fills[i] ?? " "}
            </span>
          </React.Fragment>
        ))}
        <span className="seg">{segments[nBlanks]}</span>
      </div>
    </div>
  );
};

export default DndCloze;

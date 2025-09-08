import React, { useEffect, useMemo, useRef, useState } from "react";

type Props = {
  segments: string[];         // len = n_blanks + 1
  answers: string[];          // correct answers in order
  initialBank: string[];      // starting tokens in bank (scrambled)
  initialFills: (string | null)[]; // current fills per blank (len = n_blanks)
  showFeedback: boolean;      // if true, color blanks green/red
};

const DndCloze: React.FC<Props> = ({
  segments, answers, initialBank, initialFills, showFeedback,
}) => {
  const nBlanks = answers.length;
  const [bank, setBank] = useState<string[]>(initialBank);
  const [fills, setFills] = useState<(string | null)[]>(initialFills);

  useEffect(() => {
    setBank(initialBank);
  }, [initialBank.join("|")]);

  useEffect(() => {
    setFills(initialFills);
  }, [initialFills.join("|")]);

  // Drag state
  const dragging = useRef<string | null>(null);

  const onDragStartChip = (token: string) => (e: React.DragEvent) => {
    dragging.current = token;
    e.dataTransfer.setData("text/plain", token);
    e.dataTransfer.effectAllowed = "move";
  };

  const onDropBank = (e: React.DragEvent) => {
    e.preventDefault();
    const tok = e.dataTransfer.getData("text/plain");
    if (!tok) return;
    // If token is currently in a blank, remove from that blank
    const idx = fills.findIndex(f => f === tok);
    if (idx >= 0) {
      const nf = fills.slice();
      nf[idx] = null;
      setFills(nf);
      setBank(prev => [...prev, tok]);
    }
    dragging.current = null;
  };

  const onDragOver = (e: React.DragEvent) => e.preventDefault();

  const onDropBlank = (i: number) => (e: React.DragEvent) => {
    e.preventDefault();
    const tok = e.dataTransfer.getData("text/plain");
    if (!tok) return;
    // If token is in bank, remove from bank; if in another blank, clear there
    const inBank = bank.includes(tok);
    const fromIdx = fills.findIndex(f => f === tok);

    const nf = fills.slice();
    if (fromIdx >= 0) nf[fromIdx] = null;
    if (inBank) {
      setBank(prev => prev.filter(t => t !== tok));
    }
    // If this blank already had a token, return it to bank
    if (nf[i]) {
      setBank(prev => [...prev, nf[i] as string]);
    }
    nf[i] = tok;
    setFills(nf);
    dragging.current = null;
  };

  // Classes per blank
  const blankClass = (i: number) => {
    const base = ["blank"];
    if (fills[i]) base.push("filled");
    if (showFeedback && fills[i]) {
      const ok = fills[i]!.trim().toLowerCase() === answers[i].trim().toLowerCase();
      base.push(ok ? "correct" : "wrong");
    }
    return base.join(" ");
  };

  // Component state for Streamlit (serialize outcome)
  // We return as window.postMessage via Streamlit lib upstream (handled in index.tsx)
  (window as any).__DND_CLOZE_STATE__ = { bank, fills };

  return (
    <div className="wrap">
      {/* Bank */}
      <div className="bank" onDrop={onDropBank} onDragOver={onDragOver}>
        {bank.map((tok, idx) => (
          <div
            key={tok + idx}
            className={`chip`}
            draggable
            onDragStart={onDragStartChip(tok)}
            title="Drag into a blank"
          >
            {tok}
          </div>
        ))}
      </div>

      {/* Sentence */}
      <div className="row">
        {Array.from({ length: nBlanks }).map((_, i) => (
          <React.Fragment key={`seg-${i}`}>
            <span className="seg">{segments[i]}</span>
            <span
              className={blankClass(i)}
              onDrop={onDropBlank(i)}
              onDragOver={onDragOver}
              title={fills[i] ? "Drag out to bank to remove" : "Drop a word here"}
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

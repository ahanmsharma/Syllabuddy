import React, { useEffect, useRef, useState } from "react";
import { withStreamlitConnection, Streamlit, ComponentProps } from "streamlit-component-lib";
import "./styles.css";

type Item = {
  id: string;
  title: string;
  subtitle?: string;
  selected?: boolean;
};

type Props = ComponentProps & {
  args: {
    items: Item[];
    instructions?: string;
    longPressMs?: number; // default 450
  };
};

const GestureGrid: React.FC<Props> = ({ args, disabled }) => {
  const { items, instructions, longPressMs = 450 } = args;

  // Render a card that detects double click and long-press.
  const Card: React.FC<{ item: Item }> = ({ item }) => {
    const [pressPct, setPressPct] = useState(0);
    const timerRef = useRef<number | null>(null);
    const startRef = useRef<number>(0);
    const rafRef = useRef<number | null>(null);

    const onPointerDown = (e: React.PointerEvent) => {
      if (disabled) return;
      startRef.current = performance.now();
      setPressPct(0);

      const step = () => {
        const elapsed = performance.now() - startRef.current;
        const pct = Math.min(100, (elapsed / longPressMs) * 100);
        setPressPct(pct);
        if (pct < 100) rafRef.current = requestAnimationFrame(step);
      };
      rafRef.current = requestAnimationFrame(step);

      // Fire select after longPressMs
      timerRef.current = window.setTimeout(() => {
        cleanupTimers();
        sendEvent("select", item.id);
      }, longPressMs);
    };

    const cleanupTimers = () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      setPressPct(0);
    };

    const onPointerUp = (e: React.PointerEvent) => {
      cleanupTimers();
    };
    const onPointerLeave = (e: React.PointerEvent) => {
      cleanupTimers();
    };

    const onDoubleClick = (e: React.MouseEvent) => {
      if (disabled) return;
      cleanupTimers();
      sendEvent("open", item.id);
    };

    const sendEvent = (type: "select" | "open", id: string) => {
      Streamlit.setComponentValue({ type, id });
    };

    return (
      <div
        className={`card ${item.selected ? "selected" : ""}`}
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerLeave}
        onDoubleClick={onDoubleClick}
      >
        <div className="card-title">{item.title}</div>
        {item.subtitle && <div className="card-sub">{item.subtitle}</div>}
        <div className="hint">Long-press to Select / Unselect · Double-click to Open</div>

        {/* Progress ring/bar for the long press */}
        {pressPct > 0 && (
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${pressPct}%` }} />
          </div>
        )}
      </div>
    );
  };

  useEffect(() => {
    Streamlit.setFrameHeight();
  }, [items, disabled]);

  return (
    <div className="grid">
      {items.map((it) => (
        <Card key={it.id} item={it} />
      ))}
    </div>
  );
};

export default withStreamlitConnection(GestureGrid);

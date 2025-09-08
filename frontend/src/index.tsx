import React from "react";
import { createRoot } from "react-dom/client";
import { Streamlit, withStreamlitConnection } from "streamlit-component-lib";
import DndCloze from "./DndCloze";

type Args = {
  segments: string[];
  answers: string[];
  initialBank: string[];
  initialFills: (string | null)[];
  showFeedback: boolean;
};

const App = (props: any) => {
  const args = props.args as Args;

  React.useEffect(() => {
    // Size to content
    Streamlit.setFrameHeight();
  });

  // Push state upstream whenever internal state changes (on a small interval)
  React.useEffect(() => {
    const iv = setInterval(() => {
      // @ts-ignore
      const state = (window as any).__DND_CLOZE_STATE__;
      if (state) Streamlit.setComponentValue(state);
    }, 120);
    return () => clearInterval(iv);
  }, []);

  return (
    <DndCloze
      segments={args.segments}
      answers={args.answers}
      initialBank={args.initialBank}
      initialFills={args.initialFills}
      showFeedback={args.showFeedback}
    />
  );
};

const Connected = withStreamlitConnection(App);
const root = createRoot(document.getElementById("root")!);
root.render(<Connected />);

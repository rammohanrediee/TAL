"use client";

import * as React from "react";
import { ArrowUpIcon, AtSignIcon, LoaderCircleIcon, PaperclipIcon, XIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/*
 * The composer is a set of parts around one context, after Fernando Rojo's
 * "Composition is all you need". The parts never own state: they read it and
 * call actions through the context. Whoever renders the provider decides
 * where the draft lives, so the same parts serve a local draft, an edit, or a
 * draft synced across devices without a boolean prop for each.
 */

type ChatComposerAttachment = {
  /** Stable key for the attachment. */
  id: string;
  /** File name shown on the chip. */
  name: string;
  /** Size in bytes, shown beside the name when present. */
  size?: number;
  /** The file itself, when it came from this device. */
  file?: File;
};

type ChatComposerState = {
  /** The draft text. */
  value: string;
  /** Files attached to the draft. */
  attachments: ChatComposerAttachment[];
  /** True while a submit is in flight. */
  submitting?: boolean;
  /** True when the composer takes no input. */
  disabled?: boolean;
  /** Whether the draft may be sent. Defaults to having text or an attachment. */
  canSubmit?: boolean;
};

type ChatComposerActions = {
  /** Replaces the draft text. */
  setValue: (value: string) => void;
  /** Attaches files to the draft. */
  addAttachments: (files: File[]) => void;
  /** Removes one attachment by id. */
  removeAttachment: (id: string) => void;
  /** Sends the draft. */
  submit: () => void;
};

type ChatComposerMeta = {
  /** The text box, so any part can focus it or read the caret. */
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
};

type ChatComposerContextValue = {
  /** The draft. */
  state: ChatComposerState;
  /** How to change the draft and send it. */
  actions: ChatComposerActions;
  /** Handles the parts share, such as the text box. */
  meta: ChatComposerMeta;
};

const ChatComposerContext =
  React.createContext<ChatComposerContextValue | null>(null);

/** Reads the nearest composer. Throws outside a provider. */
function useChatComposer() {
  const context = React.useContext(ChatComposerContext);
  if (!context) {
    throw new Error(
      "Composer parts must be rendered inside a ChatComposerProvider.",
    );
  }
  return context;
}

/** Whether the draft has any text or files in it. */
function hasContent({ value, attachments }: ChatComposerMessage) {
  return value.trim() !== "" || attachments.length > 0;
}

/** Whether the draft may be sent and the composer is free to send it. */
function isSubmittable(state: ChatComposerState) {
  return (
    !state.disabled &&
    !state.submitting &&
    (state.canSubmit ?? hasContent(state))
  );
}

type ChatComposerProviderProps = {
  /** The draft, from wherever it lives. */
  state: ChatComposerState;
  /** How the parts change the draft and send it. */
  actions: ChatComposerActions;
  /** A ref for the text box. One is made for you when omitted. */
  inputRef?: React.RefObject<HTMLTextAreaElement | null>;
  /** The parts, in any order and anywhere below. Renders no element. */
  children?: React.ReactNode;
};

/*
 * The seam between the parts and the state. Swap what feeds it, not the parts.
 */
function ChatComposerProvider({
  state,
  actions,
  inputRef,
  children,
}: ChatComposerProviderProps) {
  const ownRef = React.useRef<HTMLTextAreaElement>(null);
  const ref = inputRef ?? ownRef;
  const value = React.useMemo(
    () => ({ state, actions, meta: { inputRef: ref } }),
    [state, actions, ref],
  );
  return <ChatComposerContext value={value}>{children}</ChatComposerContext>;
}

type ChatComposerMessage = {
  /** The text that was sent, trimmed. */
  value: string;
  /** The files that were sent. */
  attachments: ChatComposerAttachment[];
};

type LocalChatComposerProviderProps = {
  /** The draft to start with. */
  defaultValue?: string;
  /** Attachments to start with. */
  defaultAttachments?: ChatComposerAttachment[];
  /** Called with the draft on send. Return a promise to hold the draft until it settles; a rejection keeps it. */
  onSubmit?: (message: ChatComposerMessage) => void | Promise<void>;
  /** Takes no input while true. */
  disabled?: boolean;
  /** Decides whether the draft may be sent. Defaults to having text or an attachment. */
  canSubmit?: (message: ChatComposerMessage) => boolean;
  /** A ref for the text box. One is made for you when omitted. */
  inputRef?: React.RefObject<HTMLTextAreaElement | null>;
  /** The parts. */
  children?: React.ReactNode;
};

let attachmentCount = 0;

/** Turns picked or dropped files into attachments with unique ids. */
function toAttachments(files: File[]): ChatComposerAttachment[] {
  return files.map((file) => ({
    id: `attachment-${++attachmentCount}`,
    name: file.name,
    size: file.size,
    file,
  }));
}

/*
 * The draft in component state, cleared once a send succeeds. For a draft
 * that has to outlive the component or follow the person across devices,
 * render ChatComposerProvider with your own store instead.
 */
function LocalChatComposerProvider({
  defaultValue = "",
  defaultAttachments = [],
  onSubmit,
  disabled,
  canSubmit = hasContent,
  inputRef,
  children,
}: LocalChatComposerProviderProps) {
  const [value, setValue] = React.useState(defaultValue);
  const [attachments, setAttachments] = React.useState(defaultAttachments);
  const [submitting, setSubmitting] = React.useState(false);

  const ready = canSubmit({ value: value.trim(), attachments });
  const state = React.useMemo(
    () => ({ value, attachments, submitting, disabled, canSubmit: ready }),
    [value, attachments, submitting, disabled, ready],
  );

  // Submit reads the latest draft without re-creating the actions on every
  // keystroke, which would re-render every part that only needs actions.
  const latest = React.useRef({ state, onSubmit });
  React.useLayoutEffect(() => {
    latest.current = { state, onSubmit };
  });

  const actions = React.useMemo<ChatComposerActions>(
    () => ({
      setValue,
      addAttachments: (files) =>
        setAttachments((current) => [...current, ...toAttachments(files)]),
      removeAttachment: (id) =>
        setAttachments((current) => current.filter((a) => a.id !== id)),
      submit: () => {
        const { state, onSubmit } = latest.current;
        if (!isSubmittable(state)) return;
        const message = {
          value: state.value.trim(),
          attachments: state.attachments,
        };
        // Clear only what was sent: people keep typing while a slow send is
        // in flight, and that new draft has to survive it settling.
        const sent = new Set(state.attachments.map((a) => a.id));
        const clear = () => {
          setValue((current) => (current === state.value ? "" : current));
          setAttachments((current) => current.filter((a) => !sent.has(a.id)));
        };
        const result = onSubmit?.(message);
        if (!(result instanceof Promise)) {
          clear();
          return;
        }
        setSubmitting(true);
        result.then(clear, () => {}).finally(() => setSubmitting(false));
      },
    }),
    [],
  );

  return (
    <ChatComposerProvider state={state} actions={actions} inputRef={inputRef}>
      {children}
    </ChatComposerProvider>
  );
}

const INTERACTIVE =
  "button, a, input, textarea, select, label, [role=button], [tabindex], [contenteditable]";

/*
 * The box around the parts. A click on its bare surface focuses the text box,
 * so the whole frame reads as one field.
 */
function ChatComposerFrame({
  className,
  onClick,
  ...props
}: React.ComponentProps<"div">) {
  const { state, meta } = useChatComposer();
  return (
    <div
      data-slot="chat-composer"
      data-disabled={state.disabled ? "" : undefined}
      className={cn(
        "relative flex w-full flex-col rounded-2xl border border-input bg-input-subtle transition-colors has-[[data-slot=chat-composer-input]:focus-visible]:border-ring has-[[data-slot=chat-composer-input]:focus-visible]:ring-[3px] has-[[data-slot=chat-composer-input]:focus-visible]:ring-ring-subtle data-disabled:cursor-not-allowed data-disabled:opacity-50",
        className,
      )}
      onClick={(event) => {
        onClick?.(event);
        const target = event.target as Element;
        if (event.defaultPrevented || target.closest(INTERACTIVE)) return;
        meta.inputRef.current?.focus();
      }}
      {...props}
    />
  );
}

/** A row above the text box, for context such as a reply or attachments. */
function ChatComposerHeader({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="chat-composer-header"
      className={cn(
        "flex flex-wrap items-center gap-2 px-3 pt-3 text-sm text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

/*
 * The text box. Enter sends and Shift+Enter breaks the line. To change that,
 * handle onKeyDown and call preventDefault; the part then leaves the key alone.
 */
function ChatComposerInput({
  className,
  ref,
  disabled,
  onChange,
  onKeyDown,
  "aria-label": ariaLabel = "Message",
  ...props
}: React.ComponentProps<"textarea">) {
  const {
    state,
    actions,
    meta: { inputRef },
  } = useChatComposer();
  // A caller's ref joins the composer's rather than replacing it, which
  // would break frame clicks and the mention button.
  const mergedRef = React.useCallback(
    (node: HTMLTextAreaElement | null) => {
      inputRef.current = node;
      if (typeof ref === "function") return ref(node);
      if (ref) ref.current = node;
    },
    [inputRef, ref],
  );
  return (
    <textarea
      {...props}
      ref={mergedRef}
      data-slot="chat-composer-input"
      rows={props.rows ?? 1}
      aria-label={ariaLabel}
      value={state.value}
      disabled={state.disabled || disabled}
      onChange={(event) => {
        onChange?.(event);
        actions.setValue(event.target.value);
      }}
      onKeyDown={(event) => {
        onKeyDown?.(event);
        if (
          event.defaultPrevented ||
          event.key !== "Enter" ||
          event.shiftKey ||
          // Enter also confirms a word in an input method editor. Safari
          // reports that keydown as keyCode 229 without isComposing.
          event.nativeEvent.isComposing ||
          event.keyCode === 229
        )
          return;
        event.preventDefault();
        actions.submit();
      }}
      className={cn(
        "field-sizing-content max-h-60 min-h-11 w-full resize-none bg-transparent px-3 py-3 text-base outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed md:text-sm",
        className,
      )}
    />
  );
}

/** A row below the text box, for actions and the send button. */
function ChatComposerFooter({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="chat-composer-footer"
      className={cn(
        "flex items-center justify-between gap-1 px-2 pb-2",
        className,
      )}
      {...props}
    />
  );
}

type ChatComposerActionProps = Omit<
  React.ComponentProps<typeof Button>,
  "aria-label"
> & {
  /** Names the icon for screen readers and the tooltip. */
  label: string;
};

/** An icon button for the footer, disabled with the composer. */
function ChatComposerAction({
  label,
  className,
  disabled,
  ...props
}: ChatComposerActionProps) {
  const { state } = useChatComposer();
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            data-slot="chat-composer-action"
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={label}
            disabled={disabled ?? state.disabled}
            className={cn("rounded-full text-muted-foreground", className)}
            {...props}
          />
        }
      />
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

type ChatComposerAttachButtonProps = Omit<ChatComposerActionProps, "label"> & {
  /** File types the picker offers, as in the input's accept attribute. */
  accept?: string;
  /** Whether the picker accepts more than one file. */
  multiple?: boolean;
  /** Names the button. */
  label?: string;
};

/** Opens the file picker and attaches what is picked. */
function ChatComposerAttachButton({
  accept,
  multiple = false,
  label = "Attach files",
  onClick,
  children,
  ...props
}: ChatComposerAttachButtonProps) {
  const { actions } = useChatComposer();
  const fileRef = React.useRef<HTMLInputElement>(null);
  return (
    <>
      <ChatComposerAction
        label={label}
        onClick={(event) => {
          onClick?.(event);
          if (!event.defaultPrevented) fileRef.current?.click();
        }}
        {...props}
      >
        {children ?? <PaperclipIcon />}
      </ChatComposerAction>
      <input
        ref={fileRef}
        type="file"
        multiple={multiple}
        hidden
        accept={accept}
        tabIndex={-1}
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          if (files.length) actions.addAttachments(files);
          // Picking the same file twice should attach it twice.
          event.target.value = "";
        }}
      />
    </>
  );
}

/** Puts text at the caret, replacing any selection, and keeps focus there. */
function insertAtCaret(
  { state, actions, meta }: ChatComposerContextValue,
  text: string,
) {
  const input = meta.inputRef.current;
  const start = input?.selectionStart ?? state.value.length;
  const end = input?.selectionEnd ?? state.value.length;
  actions.setValue(state.value.slice(0, start) + text + state.value.slice(end));
  const caret = start + text.length;
  requestAnimationFrame(() => {
    input?.focus();
    input?.setSelectionRange(caret, caret);
  });
}

/** Starts a mention by typing @ at the caret. */
function ChatComposerMentionButton({
  label = "Mention someone",
  onClick,
  children,
  ...props
}: Omit<ChatComposerActionProps, "label"> & {
  /** Names the button. */
  label?: string;
}) {
  const composer = useChatComposer();
  return (
    <ChatComposerAction
      label={label}
      onClick={(event) => {
        onClick?.(event);
        if (!event.defaultPrevented) insertAtCaret(composer, "@");
      }}
      {...props}
    >
      {children ?? <AtSignIcon />}
    </ChatComposerAction>
  );
}

/*
 * The actions most composers share. It is only JSX, so a composer that needs
 * something else leaves it out and lists its own actions instead.
 */
function ChatComposerCommonActions({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="chat-composer-common-actions"
      className={cn("flex items-center gap-0.5", className)}
      {...props}
    >
      <ChatComposerAttachButton />
      <ChatComposerMentionButton />
    </div>
  );
}

/** Sends the draft. Works anywhere inside the provider, not only in the frame. */
function ChatComposerSubmit({
  className,
  children,
  disabled,
  onClick,
  "aria-label": ariaLabel = "Send",
  ...props
}: React.ComponentProps<typeof Button>) {
  const { state, actions, meta } = useChatComposer();
  return (
    <Button
      data-slot="chat-composer-submit"
      type="button"
      size={children ? "sm" : "icon-sm"}
      aria-label={children ? undefined : ariaLabel}
      aria-busy={state.submitting || undefined}
      {...props}
      disabled={disabled || !isSubmittable(state)}
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented) return;
        actions.submit();
        // Sending empties the draft, which disables this button and would
        // drop focus to the page. The text box is where people go next.
        meta.inputRef.current?.focus();
      }}
      className={cn("rounded-full", className)}
    >
      {state.submitting ? (
        <LoaderCircleIcon className="size-4 animate-spin" aria-hidden="true" />
      ) : children ? null : (
        <ArrowUpIcon />
      )}
      {children}
    </Button>
  );
}

/** Lists the draft's attachments, each with a button to remove it. Renders nothing when empty. */
function ChatComposerAttachments({
  className,
  ...props
}: React.ComponentProps<"ul">) {
  const { state, actions } = useChatComposer();
  if (!state.attachments.length) return null;
  return (
    <ul
      data-slot="chat-composer-attachments"
      aria-label="Attachments"
      className={cn("flex flex-wrap gap-1.5", className)}
      {...props}
    >
      {state.attachments.map((attachment) => (
        <li
          key={attachment.id}
          data-slot="chat-composer-attachment"
          className="flex h-7 max-w-56 items-center gap-1.5 rounded-full border border-border bg-background pr-1 pl-2.5 text-xs text-foreground"
        >
          <PaperclipIcon className="size-3 shrink-0 text-muted-foreground" />
          <span className="truncate">{attachment.name}</span>
          {attachment.size !== undefined ? (
            <span className="shrink-0 text-muted-foreground">
              {formatBytes(attachment.size)}
            </span>
          ) : null}
          <button
            type="button"
            aria-label={`Remove ${attachment.name}`}
            disabled={state.disabled}
            onClick={() => actions.removeAttachment(attachment.id)}
            className="flex size-5 shrink-0 items-center justify-center rounded-full text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring-subtle disabled:pointer-events-none"
          >
            <XIcon className="size-3" />
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Sizes in the units people read them in: 512 B, 12 KB, 3.4 MB. */
function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let size = bytes / 1024;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit++;
  }
  return `${size < 10 ? size.toFixed(1).replace(/\.0$/, "") : Math.round(size)} ${units[unit]}`;
}

/** Whether a file passes an accept string such as "image/*,.pdf". */
function matchesAccept(file: File, accept?: string) {
  if (!accept?.trim()) return true;
  const name = file.name.toLowerCase();
  const type = file.type.toLowerCase();
  return accept.split(",").some((raw) => {
    const rule = raw.trim().toLowerCase();
    if (!rule) return false;
    if (rule.startsWith(".")) return name.endsWith(rule);
    if (rule.endsWith("/*")) return type.startsWith(rule.slice(0, -1));
    return type === rule;
  });
}

/*
 * Attaches files dropped anywhere inside it. Leave it out to turn drag and
 * drop off; there is no prop for that.
 */
function ChatComposerDropZone({
  className,
  children,
  label = "Drop files to attach",
  accept,
  onDragEnter,
  onDragOver,
  onDragLeave,
  onDrop,
  ...props
}: React.ComponentProps<"div"> & {
  /** Shown over the zone while files are dragged across it. */
  label?: React.ReactNode;
  /** File types it takes, as in a file input's accept attribute. Match it to the attach button's. */
  accept?: string;
}) {
  const { state, actions } = useChatComposer();
  const [dragging, setDragging] = React.useState(false);
  // dragenter and dragleave fire for every child crossed, so count them.
  const depth = React.useRef(0);

  const hasFiles = (event: React.DragEvent) =>
    !state.disabled && event.dataTransfer.types.includes("Files");

  return (
    <div
      data-slot="chat-composer-drop-zone"
      data-dragging={dragging ? "" : undefined}
      className={cn("relative", className)}
      onDragEnter={(event) => {
        // A caller's handler runs first and can take the drag over by
        // calling preventDefault, as with ChatComposerFrame's click.
        onDragEnter?.(event);
        if (event.defaultPrevented || !hasFiles(event)) return;
        event.preventDefault();
        depth.current++;
        setDragging(true);
      }}
      onDragOver={(event) => {
        onDragOver?.(event);
        if (event.defaultPrevented || !hasFiles(event)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
      }}
      onDragLeave={(event) => {
        onDragLeave?.(event);
        depth.current = Math.max(0, depth.current - 1);
        if (depth.current === 0) setDragging(false);
      }}
      onDrop={(event) => {
        onDrop?.(event);
        // Reset first, so the hint never sticks if the composer was
        // disabled mid-drag.
        depth.current = 0;
        setDragging(false);
        if (event.defaultPrevented || !hasFiles(event)) return;
        event.preventDefault();
        const files = Array.from(event.dataTransfer.files).filter((file) =>
          matchesAccept(file, accept),
        );
        if (files.length) actions.addAttachments(files);
      }}
      {...props}
    >
      {children}
      {dragging ? (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-2xl border-2 border-dashed border-ring bg-background text-sm font-medium text-foreground"
        >
          {label}
        </div>
      ) : null}
    </div>
  );
}

export {
  ChatComposerAction,
  ChatComposerAttachButton,
  ChatComposerAttachments,
  ChatComposerCommonActions,
  ChatComposerDropZone,
  ChatComposerFooter,
  ChatComposerFrame,
  ChatComposerHeader,
  ChatComposerInput,
  ChatComposerMentionButton,
  ChatComposerProvider,
  ChatComposerSubmit,
  LocalChatComposerProvider,
  useChatComposer,
  type ChatComposerActions,
  type ChatComposerAttachment,
  type ChatComposerContextValue,
  type ChatComposerMessage,
  type ChatComposerMeta,
  type ChatComposerState,
};

export default LocalChatComposerProvider;

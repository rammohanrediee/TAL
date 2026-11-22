"use client";

import { useCallback, useId, useRef, useState } from "react";
import { ChatComposer, ChatComposerDrawer, ChatSendButton } from "@astryxdesign/core/Chat";
import { Button } from "@astryxdesign/core/Button";
import { Icon } from "@astryxdesign/core/Icon";
import { Text } from "@astryxdesign/core/Text";
import { PaperClipIcon } from "@heroicons/react/24/outline";
import styles from "./chat-workspace.module.css";

const RESUME_ACCEPT = ".pdf,.docx";
const RESUME_MAX_BYTES = 5 * 1024 * 1024;

type TalChatComposerProps = {
  id?: string;
  onSend: (text: string, file: File | null) => Promise<void>;
  disabled?: boolean;
  attachedName?: string;
};

export function TalChatComposer({
  id,
  onSend,
  disabled = false,
  attachedName,
}: TalChatComposerProps) {
  const [error, setError] = useState("");
  const [value, setValue] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const fileInputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const onPickResume = useCallback((file: File | null) => {
    if (!file) {
      setResumeFile(null);
      return;
    }
    if (file.size > RESUME_MAX_BYTES) {
      setError("Résumé must be 5 MB or smaller.");
      setResumeFile(null);
      return;
    }
    setError("");
    setResumeFile(file);
  }, []);

  const performSend = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed && !resumeFile) return;
      try {
        await onSend(trimmed, resumeFile);
        setError("");
        setValue("");
        setResumeFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      } catch (caught) {
        const message =
          caught instanceof Error ? caught.message : "Could not send your message.";
        setError(message);
        setValue(text);
      }
    },
    [onSend, resumeFile],
  );

  const canSend = Boolean(value.trim() || resumeFile) && !disabled;
  const resumeLabel = resumeFile?.name ?? attachedName;

  const drawer =
    resumeLabel ? (
      <ChatComposerDrawer count={1} label="Résumé">
        <Text type="supporting" color="secondary">
          {resumeLabel}
        </Text>
      </ChatComposerDrawer>
    ) : undefined;

  return (
    <div className={styles.composerDock}>
      {error ? (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      ) : null}
      <div className={styles.composerForm}>
        <input
          ref={fileInputRef}
          id={fileInputId}
          type="file"
          accept={RESUME_ACCEPT}
          hidden
          disabled={disabled}
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            onPickResume(file);
          }}
        />
        <ChatComposer
          id={id}
          className={styles.astryxComposer}
          elevation="none"
          isDisabled={disabled}
          value={value}
          onChange={setValue}
          onSubmit={performSend}
          placeholder="Ask TAL about a role, your résumé, or your next move…"
          drawer={drawer}
          footerActions={
            <Button
              label="Attach PDF or DOCX résumé"
              variant="ghost"
              size="md"
              icon={<Icon icon={PaperClipIcon} size="sm" />}
              isIconOnly
              isDisabled={disabled}
              onClick={() => fileInputRef.current?.click()}
            />
          }
          sendButton={<ChatSendButton isDisabled={!canSend} onSend={() => performSend(value)} />}
        />
      </div>
    </div>
  );
}
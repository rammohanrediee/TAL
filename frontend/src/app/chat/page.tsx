import type { Metadata } from "next";

export const metadata:Metadata={
    title:"Chat | TAL",
    description:"Your AI-powered job search assistant"
};
export default function ChatPage(){
    return (
        <main className="flex h-dvh overflow-hidden bg-[#212121] text-white">
            <aside className="hidden w-[280px] shrink-0 flex-col border-r border-white/10 bg-[#171717] md:flex">
           <div className="flex h-14 items-center justify-between px-3">
  <div className="flex items-center gap-2">
    <div className="flex size-8 items-center justify-center rounded-full bg-white font-bold text-black">
      T
    </div>

    <span className="font-semibold">TAL</span>
  </div>

  <button
    type="button"
    aria-label="Collapse sidebar"
    className="rounded-lg px-3 py-2 text-zinc-400 hover:bg-white/10 hover:text-white"
  >
    ‹
  </button>
</div>

<div className="px-2">
  <button
    type="button"
    className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium hover:bg-white/10"
  >
    <span aria-hidden="true" className="text-xl">
      ＋
    </span>

    <span>New chat</span>
  </button>
</div>
<div className="flex-1" />
<div className="border-t border-white/10 p-2">
  <button
    type="button"
    className="flex w-full items-center rounded-lg p-2 text-left hover:bg-white/10"
  >
    <span className="min-w-0 flex-1">
      <span className="block truncate text-sm font-medium">
        Your account
      </span>

      <span className="block truncate text-xs text-zinc-500">
        Profile & settings
      </span>
    </span>

    <span aria-hidden="true" className="text-zinc-500">
      ...
    </span>
  </button>
</div>
            

            </aside>
           <section className="flex min-w-0 flex-1 flex-col">
  <div className="flex flex-1 items-center justify-center px-4">
    <div className="w-full max-w-3xl">
      <h1 className="mb-8 text-center text-2xl font-semibold sm:text-3xl">
        What can I help you with?
      </h1>

     <form className="flex min-h-14 items-center gap-2 rounded-[28px] border border-white/10 bg-[#2f2f2f] px-3 py-2 shadow-sm">
  <button
    type="button"
    aria-label="Attach a file"
    className="flex size-10 shrink-0 items-center justify-center rounded-full text-zinc-300 transition hover:bg-white/10 hover:text-white"
  >
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      className="size-6"
      aria-hidden="true"
    >
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  </button>

  <label htmlFor="message" className="sr-only">
    Message TAL
  </label>

  <textarea
    id="message"
    name="message"
    rows={1}
    placeholder="Ask TAL"
    className="h-6 flex-1 resize-none overflow-hidden bg-transparent text-base leading-6 text-white outline-none placeholder:text-zinc-400"
  />

  <button
    type="submit"
    disabled
    aria-label="Send message"
    className="flex size-10 shrink-0 items-center justify-center rounded-full bg-white text-black transition disabled:cursor-not-allowed disabled:bg-zinc-600 disabled:text-zinc-400"
  >
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      className="size-5"
      aria-hidden="true"
    >
      <path
        d="M12 19V5M6 11l6-6 6 6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  </button>
</form>

      <p className="mt-3 text-center text-xs text-zinc-500">
        TAL can make mistakes. Check important information.
      </p>
    </div>
  </div>
</section>
        </main>
    );
}

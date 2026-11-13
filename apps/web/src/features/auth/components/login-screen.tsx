"use client";

import {
  ArrowRightIcon,
  EyeIcon,
  EyeOffIcon,
  FlaskConicalIcon,
  GitCompareIcon,
  ScaleIcon,
  WaypointsIcon,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { EvalLogo, EvalMark } from "@/components/eval-logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FieldError, Label } from "@/components/ui/label";
import { errorMessage } from "@/lib/api/errors";
import { safeNext } from "@/lib/auth-redirect";

import { useLogin } from "../api";

const PITCH = [
  {
    icon: FlaskConicalIcon,
    title: "Deterministic first, judge second",
    body: "Exact match, regex, required and forbidden tool calls run with no model call at all. A judge only scores what cannot be checked for certain.",
  },
  {
    icon: WaypointsIcon,
    title: "Every score has its trace",
    body: "OpenTelemetry-shaped spans for every run, linked to the result that scored it, so a regression is something you can open and read, not just a number.",
  },
  {
    icon: GitCompareIcon,
    title: "Compare runs, not just read one",
    body: "A baseline and a candidate version produce a real delta per metric, with a regression flagged automatically.",
  },
  {
    icon: ScaleIcon,
    title: "Honest about bias",
    body: "A judge from the agent's own provider family is flagged, never silently treated as neutral. No single composite score without the breakdown.",
  },
];

export function LoginScreen() {
  const router = useRouter();
  const params = useSearchParams();
  const login = useLogin();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [show, setShow] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const expired = params.get("reason") === "expired";

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setError(null);
    login.mutate(
      { email: email.trim(), password },
      {
        onSuccess: (session) => {
          toast.success(`Welcome back, ${session.user.name.split(" ")[0]}.`);
          router.replace(safeNext(params.get("next")));
        },
        onError: (err) => setError(errorMessage(err)),
      },
    );
  }

  return (
    <div className="grid min-h-dvh bg-background lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      <div className="relative flex flex-col px-6 py-6 sm:px-10">
        <div className="flex items-center justify-between">
          <EvalLogo />
          <ThemeToggle />
        </div>
        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-[360px]">
            <h1 className="text-[26px] leading-tight font-semibold tracking-[-0.025em]">Sign in to AgentEval</h1>
            <p className="mt-1.5 text-[13.5px] text-muted-foreground">
              Measure agent quality over time, not just once.
            </p>
            {expired && (
              <div role="status" className="mt-5 rounded-lg bg-warning-soft px-3.5 py-2.5 text-[13px] text-warning">
                Your session expired. Sign in again to pick up where you left off.
              </div>
            )}
            <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  autoFocus
                  placeholder="you@company.com"
                  className="h-10"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={!!error || undefined}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={show ? "text" : "password"}
                    autoComplete="current-password"
                    className="h-10 pr-10"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    aria-invalid={!!error || undefined}
                  />
                  <button
                    type="button"
                    onClick={() => setShow((s) => !s)}
                    aria-label={show ? "Hide password" : "Show password"}
                    className="absolute top-1/2 right-2 flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-subtle hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    {show ? <EyeOffIcon className="size-4" /> : <EyeIcon className="size-4" />}
                  </button>
                </div>
              </div>
              {error && <FieldError>{error}</FieldError>}
              <Button type="submit" size="lg" className="w-full" disabled={login.isPending}>
                {login.isPending ? "Signing in..." : "Sign in"}
                {!login.isPending && <ArrowRightIcon />}
              </Button>
            </form>
            <p className="mt-6 text-xs leading-relaxed text-muted-foreground">
              Accounts are created by an owner, or by running{" "}
              <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">agenteval create-owner</code> on
              the server.
            </p>
          </div>
        </div>
        <p className="text-[11.5px] text-faint">Self-hosted. Your agents, datasets and traces never leave your infrastructure.</p>
      </div>

      <aside className="relative hidden overflow-hidden bg-[#0c0a1a] p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-90"
          style={{
            background:
              "radial-gradient(60% 50% at 80% 10%, rgba(109,91,240,0.45), transparent 70%), radial-gradient(50% 45% at 10% 90%, rgba(163,148,255,0.22), transparent 70%)",
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: "linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)",
            backgroundSize: "36px 36px",
          }}
        />
        <div className="relative flex items-center gap-2 text-[13px] font-medium text-white/70">
          <EvalMark className="size-6" />
          Open-source agent evaluation
        </div>

        <div className="relative max-w-lg">
          <h2 className="text-[34px] leading-[1.12] font-semibold tracking-[-0.03em]">
            Test it.
            <br />
            <span className="text-[#c4b5fd]">Trust the diff.</span>
          </h2>
          <p className="mt-3 text-[14.5px] leading-relaxed text-white/65">
            A new prompt, a new model version, a new tool. AgentEval scores each run against your own dataset and
            shows you exactly what changed, backed by the trace that produced it.
          </p>

          <div className="mt-8 rounded-2xl bg-white/[0.06] p-4 shadow-[0_20px_60px_rgba(0,0,0,0.35)] ring-1 ring-white/10 backdrop-blur">
            <div className="flex items-center justify-between text-[12px] text-white/55">
              <span>support-agent v3 vs v2</span>
              <span className="rounded-full bg-[#fb7185]/15 px-2 py-0.5 font-semibold text-[#fb7185]">Regression</span>
            </div>
            <div className="mt-3 font-mono text-[12px] leading-relaxed text-white/80">
              <span className="text-[#c4b5fd]">exact_match</span>: 1.00 to 0.00, delta -100%, flagged
            </div>
            <div className="mt-3 flex items-center gap-4 text-[11.5px] text-white/50">
              <span>Baseline run a3f1c9</span>
              <span>Candidate run 82a179</span>
            </div>
          </div>

          <ul className="mt-8 grid gap-5 sm:grid-cols-2">
            {PITCH.map((p) => (
              <li key={p.title} className="flex gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-white/10 text-[#ddd6fe]">
                  <p.icon className="size-4" />
                </span>
                <div>
                  <div className="text-[13px] font-semibold">{p.title}</div>
                  <div className="mt-0.5 text-[12.5px] leading-relaxed text-white/55">{p.body}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative text-[11.5px] text-white/40">MIT licensed. Part of the Euron open-source initiative.</div>
      </aside>
    </div>
  );
}

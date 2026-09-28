"use client";

import { useRef, useState } from "react";

type ResumeData = {
  name: string | null;
  email: string | null;
  phone: string | null;
  total_experience_years: number | null;
  skills: string[];
  experiences: {
    company: string | null;
    role: string | null;
    duration: string | null;
    description: string | null;
    skills_used: string[];
  }[];
  education: string[];
  projects: string[];
  certifications: string[];
};

type MatchDetails = {
  overall_score: number;
  category_scores: Record<string, number>;
  required_skills_matched: string[];
  required_skills_missing: string[];
  preferred_skills_matched: string[];
  preferred_skills_missing: string[];
  experience_requirement_met: boolean;
  education_requirement_met: boolean;
  has_projects: boolean;
  has_certifications: boolean;
  verdict: string;
};

type Candidate = {
  name: string | null;
  email: string | null;
  phone: string | null;
  score: number;
  status: string;
  details: MatchDetails;
  resume: ResumeData;
};

type Skipped = { file: string; reason: string };

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    "Strong Match": "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    "Moderate Match": "bg-amber-500/15 text-amber-400 border-amber-500/30",
    "Low Match": "bg-rose-500/15 text-rose-400 border-rose-500/30",
  };
  const style = styles[status] ?? "bg-gray-500/15 text-gray-400 border-gray-500/30";
  return (
    <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium border ${style}`}>
      {status}
    </span>
  );
}

function CandidateDetail({
  candidate,
  onClose,
}: {
  candidate: Candidate;
  onClose: () => void;
}) {
  const { resume, details } = candidate;

  return (
    <div className="mt-6 rounded-xl border border-[#23262F] bg-[#12141C] p-6">
      <div className="flex justify-between items-start mb-5">
        <div>
          <h2 className="text-lg font-semibold text-[#E4E6EB]">{resume.name ?? "Unknown candidate"}</h2>
          <p className="text-sm text-[#8B92A5] mt-0.5">
            {resume.email} {resume.phone ? `· ${resume.phone}` : ""}
          </p>
        </div>
        <button onClick={onClose} className="text-sm text-[#8B92A5] hover:text-[#E4E6EB]">
          Close
        </button>
      </div>

      <div className="mb-5 pb-5 border-b border-[#23262F]">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl font-semibold text-[#E4E6EB]">{details.overall_score}%</span>
          <StatusBadge status={candidate.status} />
        </div>
        <p className="text-sm text-[#8B92A5]">{details.verdict}</p>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-5">
        <div>
          <h3 className="text-sm font-medium text-[#E4E6EB] mb-2">Category scores</h3>
          <ul className="text-sm text-[#8B92A5] space-y-1">
            {Object.entries(details.category_scores).map(([key, value]) => (
              <li key={key} className="flex justify-between">
                <span>{key.replace(/_/g, " ")}</span>
                <span className="text-[#E4E6EB]">{value}%</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-medium text-[#E4E6EB] mb-2">Requirements</h3>
          <ul className="text-sm text-[#8B92A5] space-y-1">
            <li>Experience: {details.experience_requirement_met ? "Met" : "Not met"}</li>
            <li>Education: {details.education_requirement_met ? "Met" : "Not met"}</li>
            <li>Projects: {details.has_projects ? "Present" : "None"}</li>
            <li>Certifications: {details.has_certifications ? "Present" : "None"}</li>
          </ul>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-5">
        <div>
          <h3 className="text-sm font-medium text-[#E4E6EB] mb-2">Required skills</h3>
          <p className="text-sm text-emerald-400 mb-1">{details.required_skills_matched.join(", ") || "None matched"}</p>
          <p className="text-sm text-rose-400">{details.required_skills_missing.join(", ") || "None missing"}</p>
        </div>
        <div>
          <h3 className="text-sm font-medium text-[#E4E6EB] mb-2">Preferred skills</h3>
          <p className="text-sm text-emerald-400 mb-1">{details.preferred_skills_matched.join(", ") || "None matched"}</p>
          <p className="text-sm text-rose-400">{details.preferred_skills_missing.join(", ") || "None missing"}</p>
        </div>
      </div>

      <div className="mb-5">
        <h3 className="text-sm font-medium text-[#E4E6EB] mb-2">All skills</h3>
        <p className="text-sm text-[#8B92A5]">{resume.skills.join(", ") || "None listed"}</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="text-sm font-medium text-[#E4E6EB] mb-2">Education</h3>
          <ul className="text-sm text-[#8B92A5] space-y-1">
            {resume.education.length > 0 ? resume.education.map((e, i) => <li key={i}>{e}</li>) : <li>None listed</li>}
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-medium text-[#E4E6EB] mb-2">Projects</h3>
          <ul className="text-sm text-[#8B92A5] space-y-1">
            {resume.projects.length > 0 ? resume.projects.map((p, i) => <li key={i}>{p}</li>) : <li>None listed</li>}
          </ul>
        </div>
      </div>

      <div className="mt-5">
        <h3 className="text-sm font-medium text-[#E4E6EB] mb-2">Certifications</h3>
        <ul className="text-sm text-[#8B92A5] space-y-1">
          {resume.certifications.length > 0 ? resume.certifications.map((c, i) => <li key={i}>{c}</li>) : <li>None listed</li>}
        </ul>
      </div>
    </div>
  );
}

export default function Home() {
  const [jobDescription, setJobDescription] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [skipped, setSkipped] = useState<Skipped[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAnalyze = async () => {
    if (!jobDescription.trim()) {
      setError("Please enter a job description.");
      return;
    }
    if (!files || files.length === 0) {
      setError("Please upload at least one resume.");
      return;
    }

    setError(null);
    setLoading(true);
    setCandidates([]);
    setSkipped([]);
    setSelectedIndex(null);

    try {
      const formData = new FormData();
      formData.append("job_description", jobDescription);
      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }

      const response = await fetch("http://127.0.0.1:8000/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      setCandidates(data.candidates);
      setSkipped(data.skipped ?? []);
    } catch {
      setError("Something went wrong while analyzing. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const fileNames = files ? Array.from(files).map((f) => f.name) : [];

  return (
    <div className="min-h-screen w-full bg-[#0A0C12] text-[#E4E6EB]">
      <main className="max-w-2xl mx-auto px-6 py-14">
        <div className="text-center mb-10">
          <h1 className="text-2xl font-semibold">Resume Matcher</h1>
          <p className="text-sm text-[#8B92A5] mt-1.5">
            Paste a job description, upload resumes, and see who fits — scored, not guessed.
          </p>
        </div>

        <div className="rounded-xl border border-[#23262F] bg-[#12141C] p-6 mb-5">
          <h2 className="text-sm font-medium text-[#E4E6EB] mb-3">Resumes</h2>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              setFiles(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg py-10 text-center cursor-pointer transition-colors ${
              isDragging ? "border-indigo-400 bg-indigo-500/5" : "border-[#2E3240] hover:border-[#3C4152]"
            }`}
          >
            <p className="text-sm text-[#8B92A5]">
              Drag & drop resumes here, or{" "}
              <span className="text-indigo-400 font-medium">click to browse</span>
            </p>
            <p className="text-xs text-[#5C6272] mt-1">Supports PDF and DOCX, up to 5 MB each</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            multiple
            onChange={(e) => setFiles(e.target.files)}
            className="hidden"
          />
          {fileNames.length > 0 && (
            <p className="text-sm text-[#8B92A5] mt-3">
              {fileNames.length} file{fileNames.length > 1 ? "s" : ""} selected: {fileNames.join(", ")}
            </p>
          )}
        </div>

        <div className="rounded-xl border border-[#23262F] bg-[#12141C] p-6 mb-5">
          <h2 className="text-sm font-medium text-[#E4E6EB] mb-3">Job description</h2>
          <textarea
            className="w-full bg-[#0A0C12] border border-[#23262F] rounded-lg p-3 h-40 text-sm text-[#E4E6EB] placeholder:text-[#5C6272] focus:outline-none focus:border-indigo-400"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description here..."
          />
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="w-full py-3 rounded-lg font-medium text-white bg-gradient-to-r from-indigo-500 to-teal-400 hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {loading ? "Analyzing..." : "Analyze candidates"}
        </button>

        {error && (
          <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-300 text-sm p-3">
            {error}
          </div>
        )}

        {skipped.length > 0 && (
          <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 text-sm p-3">
            <p className="font-medium mb-1">Some files were skipped</p>
            <ul className="list-disc pl-4 space-y-0.5">
              {skipped.map((s, i) => (
                <li key={i}>
                  <span className="font-medium">{s.file}</span> — {s.reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {candidates.length > 0 && (
          <div className="mt-8 rounded-xl border border-[#23262F] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-[#12141C] text-[#8B92A5]">
                <tr>
                  <th className="text-left font-medium px-4 py-3">Candidate</th>
                  <th className="text-right font-medium px-4 py-3">Score</th>
                  <th className="text-left font-medium px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c, i) => (
                  <tr
                    key={i}
                    onClick={() => setSelectedIndex(i)}
                    className={`cursor-pointer border-t border-[#23262F] transition-colors ${
                      selectedIndex === i ? "bg-indigo-500/10" : "hover:bg-[#12141C]"
                    }`}
                  >
                    <td className="px-4 py-3 text-[#E4E6EB]">{c.name ?? "Unknown"}</td>
                    <td className="px-4 py-3 text-right text-[#E4E6EB]">{c.score}%</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selectedIndex !== null && candidates[selectedIndex] && (
          <CandidateDetail candidate={candidates[selectedIndex]} onClose={() => setSelectedIndex(null)} />
        )}
      </main>
    </div>
  );
}

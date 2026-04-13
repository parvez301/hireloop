import type { Message } from '../../lib/api';
import { BatchProgressCard } from './cards/BatchProgressCard';
import { CvOutputCard } from './cards/CvOutputCard';
import { EvaluationCard } from './cards/EvaluationCard';
import { InterviewPrepCard } from './cards/InterviewPrepCard';
import { NegotiationCard } from './cards/NegotiationCard';
import { ScanProgressCard } from './cards/ScanProgressCard';
import { ScanResultsCard } from './cards/ScanResultsCard';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  return (
    <ul className="flex flex-col gap-4">
      {messages.map((message) => (
        <li
          key={message.id}
          className={
            message.role === 'user'
              ? 'self-end max-w-[85%] rounded-lg bg-[#2383e2] px-4 py-2 text-white'
              : 'self-start max-w-[85%] space-y-3'
          }
        >
          {message.role === 'user' ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="rounded-lg bg-[#f7f6f3] px-4 py-3">
              {message.content && (
                <p className="whitespace-pre-wrap text-sm">{message.content}</p>
              )}
              {message.cards?.map((card, idx) =>
                card.type === 'evaluation' ? (
                  <EvaluationCard key={idx} data={card.data as never} />
                ) : card.type === 'cv_output' ? (
                  <CvOutputCard key={idx} data={card.data as never} />
                ) : card.type === 'scan_progress' ? (
                  <ScanProgressCard key={idx} data={card.data as never} />
                ) : card.type === 'scan_results' ? (
                  <ScanResultsCard key={idx} data={card.data as never} />
                ) : card.type === 'batch_progress' ? (
                  <BatchProgressCard key={idx} data={card.data as never} />
                ) : card.type === 'interview_prep' ? (
                  <InterviewPrepCard key={idx} data={card.data as never} />
                ) : card.type === 'negotiation' ? (
                  <NegotiationCard key={idx} data={card.data as never} />
                ) : null,
              )}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

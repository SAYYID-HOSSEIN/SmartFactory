import React, {useState} from 'react';
import classNames from 'classnames';
import {Message} from "./ChatAssistant";

export class XAISources {
    // base it off the explanation interface
    response_segment: string;
    context?: string;
    source_name?: string;
    similarity_score?: number;
    original_context?: string;

    constructor(response_segment: string, context?: string, source_name?: string, similarity_score?: number, original_context?: string) {
        this.response_segment = response_segment;
        this.context = context;
        this.source_name = source_name;
        this.similarity_score = similarity_score;
        this.original_context = original_context;
    }

}

interface MessageProps {
    message: Message;
    onNavigate: (target: string, metadata: any) => void;
}

const MessageBubble: React.FC<MessageProps> = ({ message, onNavigate }) => {
    return (
        <div
            className={classNames(
                'w-fit max-w-[70%] px-4 py-2 rounded-lg text-sm text-start font-semibold shadow-md',
                message.sender === 'user'
                    ? 'bg-blue-200 text-white'
                    : 'bg-gray-200 text-gray-800'
            )}
        >
            <div className="text-xs text-gray-600">
                {message.sender === 'user' ? 'You' : 'Assistant'}
            </div>
            <p>{message.content}</p>
            {message.extraData && <ExtraDataButtons extraData={message.extraData} onNavigate={onNavigate} />}
        </div>
    );
};

interface ExtraDataProps {
    extraData: {
        explanation?: XAISources[];
        dashboardData?: { target: string; metadata: any };
    };
    onNavigate: (target: string, metadata: any) => void;
}

const ExtraDataButtons: React.FC<ExtraDataProps> = ({ extraData, onNavigate }) => {
    const [isExplanationOpen, setIsExplanationOpen] = useState(false);

    const toggleExplanation = () => setIsExplanationOpen((prev) => !prev);

    const metadata = extraData.dashboardData;
    const openSourceInNewWindow = (source: string | undefined) => {
        //TODO Implement this
    };
    return (
        <div className="mt-2 space-y-2">
            {/* Explanation Button */}
            {extraData.explanation && (
                <>
                    <button
                        onClick={toggleExplanation}
                        className="inline-block px-4 py-2 text-white bg-blue-500 hover:bg-blue-600 rounded-lg text-sm shadow-md focus:outline-none"
                    >
                        {isExplanationOpen ? "Hide Explanation" : "View Explanation"}
                    </button>
                    {isExplanationOpen && (
                        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                            <div className="bg-white rounded-lg shadow-lg p-4 max-w-lg w-full">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="text-lg font-bold text-gray-800">Explanation</h3>
                                    <button
                                        onClick={toggleExplanation}
                                        className="text-gray-600 hover:text-gray-800"
                                        aria-label="Close"
                                    >
                                        ×
                                    </button>
                                </div>

                                {/* Loop through the explanation segments */}
                                {extraData.explanation.map((segment, index) => (
                                    <div key={index} className="mb-4">
                                        <div className="font-semibold text-lg">{segment.response_segment}</div>
                                        {segment.context && (
                                            <div className="italic text-gray-700 mb-2">Context: {segment.context}</div>
                                        )}
                                        {segment.source_name && (
                                            <div className="text-blue-600 mb-2 cursor-pointer" onClick={() => openSourceInNewWindow(segment?.source_name)}>
                                                Source: {segment.source_name}
                                            </div>
                                        )}
                                        {segment.similarity_score !== undefined && (
                                            <div className="text-sm text-gray-600">
                                                Similarity Score: {segment.similarity_score.toFixed(2)}
                                            </div>
                                        )}
                                    </div>
                                ))}

                                <div className="mt-4 text-right">
                                    <button
                                        onClick={toggleExplanation}
                                        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                                    >
                                        Close
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Dashboard Navigation Button */}
            {metadata && (
                <button
                    onClick={() => onNavigate("dashboards/new", metadata.metadata)}
                    className="inline-block px-4 py-2 text-white bg-green-500 hover:bg-green-600 rounded-lg text-sm shadow-md focus:outline-none"
                >
                    Go to Dashboard
                </button>
            )}
        </div>
    );
};

export default MessageBubble;
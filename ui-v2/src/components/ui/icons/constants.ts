import {
	AlignVerticalJustifyStart,
	Ban,
	Bot,
	Calendar,
	Check,
	ChevronDown,
	ChevronLeft,
	ChevronRight,
	ChevronsLeft,
	ChevronsRight,
	CircleArrowOutUpRight,
	CircleCheck,
	Clock,
	ExternalLink,
	Loader2,
	MoreHorizontal,
	MoreVertical,
	PanelLeft,
	Pause,
	Play,
	Plus,
	Rocket,
	Search,
	ServerCrash,
	Variable,
	Workflow,
	X,
} from "lucide-react";

export const ICONS = {
	AlignVerticalJustifyStart,
	Ban,
	Bot,
	Calendar,
	Check,
	ChevronDown,
	ChevronLeft,
	ChevronRight,
	ChevronsLeft,
	ChevronsRight,
	CircleArrowOutUpRight,
	CircleCheck,
	Clock,
	ExternalLink,
	Loader2,
	MoreHorizontal,
	MoreVertical,
	PanelLeft,
	Pause,
	Play,
	Plus,
	Rocket,
	Search,
	ServerCrash,
	Variable,
	Workflow,
	X,
} as const;

export type IconId = keyof typeof ICONS;

%%======== Pckage options and base class ========
%\newboolean{logo}

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{dataflow}
\LoadClassWithOptions{article}
\RequirePackage{iftex}
\ifPDFTeX
  \pdfoutput=1
\fi
\makeatletter

% Layout 
\RequirePackage[top=2.75cm, bottom=2.5cm, left=2.5cm, right=2.5cm, columnsep=0.65cm]{geometry}
\RequirePackage{microtype}
\RequirePackage{placeins}
\RequirePackage{hyphenat}
\RequirePackage{setspace}
\RequirePackage{parskip}
\RequirePackage[latin, english]{babel}
\RequirePackage{lipsum}
\RequirePackage{etoolbox}
\RequirePackage{fancyhdr}  % custom headers/footers
\RequirePackage{ulem}  % 引用下划线
% Some engines used by tectonic/xetex report \DisableLigatures as a
% recoverable microtype error. Guard it so the technical report builds on
% the bundled OpenDCAI template without requiring pdftex-specific features.
\ifPDFTeX
  \DisableLigatures[f]{family=sf*}
\fi
\RequirePackage{graphicx}
\RequirePackage{subcaption}


\RequirePackage{booktabs}
\RequirePackage{nicematrix}
\RequirePackage{multirow}
\RequirePackage{bm}
\newcommand{\nm}[1]{#1}
\RequirePackage[most]{tcolorbox}
\RequirePackage{xcolor}
\definecolor{seedbg}{HTML}{00349F}
\definecolor{dcaiblue}{HTML}{00349F}
\definecolor{boxbg}{HTML}{F0F8FF} 
\newcommand{\dcaiblue}[1]{{\bfseries\color[HTML]{00349F} #1}} 

% References %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\RequirePackage{hyperref}
\RequirePackage[noabbrev,nameinlink]{cleveref}
\hypersetup{
  colorlinks,
  linkcolor=dcaiblue,
  citecolor=dcaiblue,
  urlcolor=dcaiblue
}

\RequirePackage[numbers, sort&compress]{natbib}
%\RequirePackage[round,authoryear]{natbib}
\def\bibfont{\small}

%%========  Bibliography using bibtex ========
\addto{\captionsenglish}{\renewcommand{\refname}{References}}
\newcommand{\citeas}[1]{\Needspace*{8\baselineskip}\noindent\bibentry{#1}}

% Section and caption format 
\newcommand{\sectionfont}
{\fontsize{12}{10}\selectfont} 

\newcommand{\subsectionfont}
{\fontsize{11}{10}\selectfont} 

\RequirePackage{titlesec}
\titleformat*{\paragraph}{\itshape}
\titleformat*{\section}{\sectionfont\sffamily\bfseries\dcaiblue}
\titleformat*{\subsection}{\subsectionfont\sffamily\bfseries\dcaiblue}

%一级二级三级标题用12 11 10
\titleformat*{\subsubsection}{\normalsize\sffamily\bfseries\dcaiblue}

\newcommand{\bffont}
{\fontsize{8.8}{10}\selectfont} 

\DeclareTextFontCommand{\textbf}{\bffont\bfseries\sffamily}

\RequirePackage{caption}
\DeclareCaptionLabelSeparator{custom}{}
\DeclareCaptionFormat{custom}{{\sffamily\textbf{#1 #2}} #3}
\captionsetup{singlelinecheck=true,format=custom,labelsep=custom,font=small}
\captionsetup[sub]{singlelinecheck=true,format=custom,labelsep=custom,font=small}


\RequirePackage[T1]{fontenc}
\DeclareFontFamily{T1}{bytesans}{}
\DeclareFontShape{T1}{bytesans}{m}{n}{<-> s * [1] DataFlow/bytesans}{}
\pdfmapline{+bytesans < DataFlow/ByteSans-Bold.ttf <T1-WGL4.enc}
\renewcommand{\sfdefault}{bytesans}%


\DeclareFontFamily{T1}{bytesansmedium}{}
\DeclareFontShape{T1}{bytesansmedium}{m}{n}{<-> s*[1] DataFlow/bytesansmedium}{}
\pdfmapline{+bytesansmedium < DataFlow/ByteSans-Medium.ttf <T1-WGL4.enc}
%\renewcommand{\sfdefault}{bytesansmedium}%
\renewcommand{\rmdefault}{cmr}
% \renewcommand{\rmdefault}{ptm} 

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Authors, affiliations, infos %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\renewcommand\addtolist[5][]{
  \begingroup
    \if\relax#3\relax\def\sep{}\else\def\sep{#5}\fi
    \let\protect\@unexpandable@protect 
    \xdef#3{\expandafter{#3}\sep #4[#1]{#2}}%
  \endgroup
}

\newcommand{\authorfont}
{\fontsize{12}{14}\selectfont} 

\newcommand\authorlist{}
\newcommand\authorformat[2][]{\authorfont {\sffamily #2$^{#1}$}}
\renewcommand\author[2][]{\addtolist[#1]{#2}{\authorlist}{\authorformat}{, }}

%给affiliation换成medium字体

\newcommand{\affiliationfont}
{\fontsize{10}{12}\selectfont}

\newcommand\affiliationlist{}
\newcommand\affiliationformat[2][]{{\affiliationfont {\fontfamily{bytesansmedium}\selectfont $^{#1}$#2}}}
\newcommand\affiliation[2][]{\addtolist[#1]{#2}{\affiliationlist}{\affiliationformat}{, }}

\newcommand{\contributionfont}
{\fontsize{10}{12}\selectfont}

\newcommand\contributionlist{}
\newcommand\contributionformat[2][]{{\contributionfont $^{#1}$#2}}
\newcommand\contribution[2][]{\addtolist[#1]{#2}{\contributionlist}{\contributionformat}{, }}

\newcommand{\checkdatafont}
{\fontsize{7.92}{10}\selectfont}

\newcommand\checkdatalist{}
\newcommand\checkdataformat[2][]{{\small {\checkdatafont\sffamily \bfseries #1:} #2}}
\newcommand\checkdata[2][]{\addtolist[#1]{#2}{\checkdatalist}{\checkdataformat}{\par}}


\newcommand{\abstractinfont}
{\fontsize{10}{12}\selectfont} 

\renewcommand{\abstract}[1]{\def\abstractlist{{\abstractinfont #1}}}
\newcommand{\email}[1]{\href{mailto:#1}{\texttt{#1}}}

\newcommand{\titlefont}
{\fontsize{17}{20}\selectfont} 

\newcommand{\thetitletext}{} 
\renewcommand{\title}[1]{
    \renewcommand{\thetitletext}{#1} 
    \newcommand{\titlelist}{\titlefont{\sffamily #1}}
}

\newcommand{\abstractfont}
{\fontsize{12}{12}\selectfont} 

\newcommand{\beginabstract}{\abstractfont{\sffamily\bfseries \dcaiblue{Abstract}\par}}

\newcommand{\beginappendix}{\appendix{\titlefont\sffamily \dcaiblue{Appendix}\par}}


\usepackage[subfigure]{tocloft}
\renewcommand{\cftsecleader}{\cftdotfill{\cftdotsep}} 
\renewcommand{\cftsecfont}{\sffamily}
%\renewcommand{\cftsubsecfont}{\sffamily\large}
\renewcommand{\cftsecpagefont}{\sffamily}{\color{dcaiblue}}
\renewcommand{\cfttoctitlefont}
{\sffamily\sectionfont\dcaiblue}


%%======== Header and Footer Content ========
\fancypagestyle{firststyle}{
    \fancyhf{} % Clear all header and footer fields for this style
    \renewcommand{\headrulewidth}{0pt} % Ensure no header rule on the first page

    \fancyhead[L]{
        \vskip 4mm
        \includegraphics[width=43.52mm,height=12.48mm]{DataFlow/OpenDCAI_logo.pdf}  
    }
    \fancyhead[R]{
        \raisebox{3mm}{ 
            \sffamily  % 使用类定义的无衬线字体 (bytesans)
            \textcolor[HTML]{4D4D4D}{\today} % 打印我们之前存储的日期
        }
    }
}

\pagestyle{fancy}
\fancyhf{} 
\fancyhead[C]{\sffamily\bfseries\color{dcaiblue}\thetitletext}
\fancyfoot[C]{\thepage} 
\renewcommand{\headrulewidth}{0.5pt} 
\renewcommand{\headrule}{\color{dcaiblue}\hrule width\headwidth height\headrulewidth \vskip-\headrulewidth} 

\renewcommand{\footrulewidth}{0pt}

% rules for title box at top of first page
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\makeatletter
\newcommand{\DMToptitlebar}{
  \dcaiblue{\hrule height 0.5pt }
  \vskip 3mm 
}
\newcommand{\DMBottomtitlebar}{
  \vskip 6mm
  \dcaiblue{\hrule height 0.5pt}
}


% Titlebox %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\newcommand{\mymaketitle}{%
  % --- 步骤 1: 首先画出页面顶部的横线 ---
  \DMToptitlebar
  
  % --- 步骤 2: 开始一个新的 tcolorbox，包裹下方所有内容 ---
  \begin{tcolorbox}[
    enhanced,
    colback=boxbg,      
    frame hidden,       
    arc=3mm,            
    left=8mm, right=8mm, top=8mm, bottom=8mm 
  ]
      
      \setlength{\parskip}{0mm}
      % \centering
      \nohyphens
      
      % 标题
      {\raggedright\titlelist\par}
      \vskip 6mm
      
      % 作者、单位、贡献
      {\centering
        \authorlist\par
      }
      \vskip 3mm
      {\centering
      \affiliationlist\par
      }
      \vskip 3mm

   
      % 摘要和底部信息
      \setlength{\parindent}{0cm}
      \setlength{\parskip}{0cm}
      
      % \begin{center}
      %     \beginabstract
      %     \vskip 3mm
      % \end{center}
    
      \abstractlist\par
      \vskip 5mm 

    \contributionlist\par
      \vskip 5mm   % 增大摘要与上方的间距
      {
        \setlength{\parskip}{0cm}
        \ifdefempty{\checkdatalist}{\vspace*{0.65cm}}{\checkdatalist\par}
      }
      
  \end{tcolorbox} 
  
  \tcbset{reset} 
  \FloatBarrier

  % 应用第一页的页眉样式
  \thispagestyle{firststyle}
}


\if@twocolumn%
\renewcommand{\maketitle}{
\twocolumn[%
 \vskip 3mm
  \mymaketitle
  \vskip 8mm
]
}%
\else%
\renewcommand{\maketitle}{
  \mymaketitle
  \vskip 8mm
}%
\fi
\makeatother

function render_figures(root, outDir, tableDir)
%RENDER_FIGURES Draw every data figure and write the result tables.
%   render_figures() uses the repository that holds this file and writes
%   Figures/<name>.png (300 dpi) and .pdf, plus Figures/tables/<name>.tex.
%   Run from the repository root:
%       matlab -batch "addpath('Analysis/matlab'); render_figures"
%   The plot data comes from the Python scripts listed in Analysis/matlab/README.md.
%   The QDrone2 traces live outside the repository; set QDRONE_TRACES to the CSV
%   written by Analysis.plot_qdrone_response (default /tmp/multirotor-qdrone-source/qdrone-traces.csv).
%   Each figure runs in its own try/catch, so one failure does not stop the rest.

here = fileparts(mfilename('fullpath'));
if nargin < 1 || isempty(root), root = fileparts(fileparts(here)); end
if nargin < 2 || isempty(outDir), outDir = fullfile(root, 'Figures'); end
if nargin < 3 || isempty(tableDir), tableDir = fullfile(outDir, 'tables'); end
if ~isfolder(outDir), mkdir(outDir); end
if ~isfolder(tableDir), mkdir(tableDir); end

S = fig_style();
% Three parameter tiers cannot be avoided: MATLAB default colours 1 and 2 for the
% nominal and worst tiers, and default colour 4 (purple) for the best tier,
% because default colour 3 (yellow) is too light for text on white.
S.tier.nominal = S.c.blue;
S.tier.worst = S.c.orange;
S.tier.best = [0.4940 0.1840 0.5560];

data = fullfile(root, 'Data', 'figure-data');
traces = getenv('QDRONE_TRACES');
if isempty(traces), traces = '/tmp/multirotor-qdrone-source/qdrone-traces.csv'; end

jobs = {
    'release_recovery_timeseries', @() make_release_timeseries(data, outDir, S)
    'release_recovery_envelope',   @() make_release_envelope(root, data, outDir, S)
    'survivable_set_psafe',        @() make_survivable_psafe(data, outDir, '', S)
    'survivable_set_psafe_a2',     @() make_survivable_psafe(data, outDir, '_a2', S)
    'survivable_set_policy',       @() make_survivable_policy(data, outDir, '', S)
    'survivable_set_policy_a2',    @() make_survivable_policy(data, outDir, '_a2', S)
    'nanobench-baseline',          @() make_nanobench_baseline(data, outDir, S)
    'qdrone-development-response', @() make_qdrone_response(root, traces, outDir, S)
    'result tables',               @() make_results_tables(root, tableDir)
    };
failed = 0;
for k = 1:size(jobs, 1)
    try
        jobs{k, 2}();
        fprintf('[ok] %s\n', jobs{k, 1});
    catch err
        failed = failed + 1;
        fprintf(2, '[failed] %s: %s\n', jobs{k, 1}, err.message);
        for s = err.stack(1:min(3, end))'
            fprintf(2, '    at %s line %d\n', s.name, s.line);
        end
    end
    close all force
end
fprintf('%d of %d jobs failed\n', failed, size(jobs, 1));
end

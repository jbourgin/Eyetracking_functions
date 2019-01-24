import re #To format data lists
from eyetracking.eyelink import *
from eyetracking.smi import *
from eyetracking.experiment import *
from eyetracking.interest_region import *
from eyetracking.scanpath import *
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication

class Make_Eyelink(Eyelink):
    def __init__(self):
        super().__init__()
        # Center of the screen.
        self.screen_center = (683,384)
        # Minimal distance at which we consider the subject is looking at the
        # fixation cross at the trial beginning
        self.valid_distance_center = 100 #3 degres of visual angle 95 (+ marge)

        # Initializing regions of interest
        self.half_width = 200
        self.half_height = 150

        # frames
        self.right = RectangleRegion((self.screen_center[0]+300, self.screen_center[1]), self.half_width, self.half_height)
        self.left = RectangleRegion((self.screen_center[0]-300, self.screen_center[1]), self.half_width, self.half_height)
        self.right_wide = RectangleRegion((self.screen_center[0]+300, self.screen_center[1]), self.half_width+10, self.half_height+10)
        self.left_wide = RectangleRegion((self.screen_center[0]-300, self.screen_center[1]), self.half_width+10, self.half_height+10)

    # Returns a dictionary of experiment variables
    def parseVariables(self, line: List[str]):
        if len(line) > 3 and line[3] == "stim1":
            try:
                if len(line) > 3 and line[3] == "stim1":
                    stim1 = line[5]
                    stim2 = line[10]
                    arrow = line[15]
                    emotion = line[20]
                return {
                    'stim1' : stim1,
                    'stim2' : stim2,
                    'arrow' : arrow,
                    'emotion' : emotion
                    }

            except:
                pass
        elif len(line) > 3 and line[3] == "target_side":
            try:
                if len(line) > 3 and line[3] == "target_side":
                    target_side = line[5]
                    position_emo = line[10]
                    position_neu = line[15]
                return {
                    'target_side' : target_side,
                    'position_emo' : position_emo,
                    'position_neu' : position_neu,
                    }

            except:
                pass
        return None

    def isResponse(self, line: Line) -> bool :
        return len(line) >= 2 and 'END' in line[0] and 'SAMPLES' in line[2]

    def isTraining(self, trial) -> bool:
        return 'Dis' in trial.features['stim1']

class Visual_selection(Experiment):

    def __init__(self):
        super().__init__(None)
        logTrace ('Number of trials to change', Precision.TITLE)
        self.n_trials = 9 #80

    def selectEyetracker(self, input_file : str) -> None:
        logTrace ('Selecting Eyelink', Precision.NORMAL)
        self.eyetracker = Make_Eyelink()

    def processTrial(self, subject, trial, filename = None):
        logTrace ('Processing trial n°%i' % trial.getTrialId(), Precision.DETAIL)
        trial_number = trial.getTrialId()

        start_trial_time = trial.getStartTrial().getTime()

        if trial.saccades == []:
            logTrace ("Subject %i has no saccades at trial %i !" %(subject.id,trial_number), Precision.DETAIL)
            first_saccade = None
        else:
            first_saccade = trial.saccades[0].getStartTime() - start_trial_time

        if trial.isTraining():
            emo_position = self.eyetracker.left
            neu_position = self.eyetracker.right
        else:
            if 'left' in trial.features['target_side']:
                emo_position = self.eyetracker.left
                neu_position = self.eyetracker.right
            elif 'right' in trial.features['target_side']:
                emo_position = self.eyetracker.right
                neu_position = self.eyetracker.left
        regions = InterestRegionList([emo_position, neu_position])


        targetname = trial.features['stim1']

        response_entry = trial.getResponse()

        region_fixations = trial.getFixationTime(regions, emo_position)

        # First fixations
        try:
            first_fixation = next(fixation for fixation in region_fixations)
        except:
            first_fixation = None

        try:
            first_emo_fixation = next(fixation for fixation in region_fixations if fixation['target'])
            capture_delay_emo_first = first_emo_fixation['begin'].getTime() - start_trial_time
        except:
            first_emo_fixation = None
            capture_delay_emo_first = None

        try:
            first_neu_fixation = next(fixation for fixation in region_fixations if not fixation['target'])
            capture_delay_neu_first = first_neu_fixation['begin'].getTime() - start_trial_time
        except:
            first_neu_fixation = None
            capture_delay_neu_first = None

        # Time on target and distractors
        total_emo_fixation_time = sum(x['time'] for x in region_fixations if x['target'])
        if total_emo_fixation_time == 0:
            total_emo_fixation_time = None
        total_neu_fixation_time = sum(x['time'] for x in region_fixations if not x['target'])
        if total_neu_fixation_time == 0:
            total_neu_fixation_time = None

        # Determining blink category
        if trial.blinks == []:
            blink_category = "No blink"
        else:
            if first_fixation is not None:
                if trial.blinks[0].getStartTime() < first_fixation['begin'].getTime():
                    blink_category = "early capture"
                else:
                    blink_category = "late"
            else:
                blink_category = None

        if trial.features['arrow'] ==  trial.features['target_side']:
            first_image_to_look = 'EMO'
        elif trial.features['arrow'] !=  trial.features['target_side']:
            first_image_to_look = 'NEU'

        # Error :
        if (not trial.isStartValid(self.eyetracker.screen_center, self.eyetracker.valid_distance_center)
            or blink_category == 'early capture' or first_fixation is None):
            #or capture_delay_first < 100):
            error = '#N/A'
        else:
            if trial.isTraining():
                error = '0'
            else:
                if ((first_fixation['target'] and trial.features['arrow'] == trial.features['target_side'])
                    or (not first_fixation['target'] and trial.features['arrow'] != trial.features['target_side'])):
                    error = '0'
                else:
                    error = '1'

        # Writing data in result csv file
        s = [str(subject.id) + "-E", # Subject name
            subject.group,
            trial_number,
            #trial.features['session'],
            trial.isTraining(),
            trial.eye,
            trial.features['emotion'],
            first_image_to_look,
            trial.features['stim1'],
            trial.features['stim2'],
            trial.features['target_side'],
            trial.features['arrow'],
            trial.features['position_emo'],
            trial.features['position_neu'],
            error,
            capture_delay_emo_first,
            capture_delay_neu_first,
            total_emo_fixation_time,
            total_neu_fixation_time,
            blink_category,
            first_saccade]

        if filename is None:
            f = open(getResultsFile(), 'a')
        else:
            f = open(filename, 'a')
        f.write(';'.join([str(x) for x in s]))
        f.write('\n')
        f.close()

    def postProcess(self, filename: str):
        logTrace ('Post process to check', Precision.TITLE)
        with open(filename) as datafile:
            data = datafile.read()
        data_modified = open(filename, 'w')
        data = data.split('\n')
        data = [x.split(';') for x in data]
        subject = "Subject"
        sequence = []
        data_seq = []

        for line in data:
            if line[0] == "Subject":
                new_line = line
                new_line.append('First fixation emo sorting')
                new_line.append('First fixation neu sorting')
                s = ";".join([str(e) for e in new_line]) + "\n"
                data_modified.write(s)
            if line[0] != subject:
                data_seq.append(sequence)
                sequence = [line]
                subject = line[0]
            else:
                sequence.append(line)
        data = data_seq[1:]


        for subject in data:
            sum_dic = {}
            counter_dic = {}
            mean_dic = {}
            SS_dic = {}
            counter_SS_dic = {}
            SD_dic = {}

            for line in subject:
                emotion = line[5]
                first_image_to_look = line[6]
                error = line[13]
                first_emo = line[14]
                first_neu = line[15]
                blink = line[16]
                code = first_image_to_look + emotion
                if code not in sum_dic:
                    sum_dic[code] = {}
                    counter_dic[code] = {}
                    mean_dic[code] = {}
                    sum_dic[code]['first_emo'] = 0
                    counter_dic[code]['first_emo'] = 0
                    mean_dic[code]['first_emo'] = None
                    sum_dic[code]['first_neu'] = 0
                    counter_dic[code]['first_neu'] = 0
                    mean_dic[code]['first_neu'] = None
                if first_emo != 'None' and "early" not in blink:
                    sum_dic[code]['first_emo'] += float(first_emo)
                    counter_dic[code]['first_emo'] += 1
                if first_neu != 'None' and "early" not in blink:
                    sum_dic[code]['first_neu'] += float(first_neu)
                    counter_dic[code]['first_neu'] += 1

            for code in mean_dic:
                for key in mean_dic[code]:
                    if sum_dic[code][key] != 0:
                        mean_dic[code][key] = sum_dic[code][key]/counter_dic[code][key]

            for line in subject:
                emotion = line[5]
                first_image_to_look = line[6]
                error = line[13]
                first_emo = line[14]
                first_neu = line[15]
                blink = line[16]
                code = first_image_to_look + emotion
                if code not in SS_dic:
                    SS_dic[code] = {}
                    counter_SS_dic[code] = {}
                    SD_dic[code] = {}
                    SS_dic[code]['first_emo'] = 0
                    counter_SS_dic[code]['first_emo'] = 0
                    SD_dic[code]['first_emo'] = None
                    SS_dic[code]['first_neu'] = 0
                    counter_SS_dic[code]['first_neu'] = 0
                    SD_dic[code]['first_neu'] = None
                if first_emo != "None" and "early" not in blink:
                    SS_dic[code]['first_emo'] += squareSum(float(first_emo), mean_dic[code]['first_emo'])
                    counter_SS_dic[code]['first_emo'] += 1
                if first_neu != "None" and "early" not in blink:
                    SS_dic[code]['first_neu'] += squareSum(float(first_neu), mean_dic[code]['first_neu'])
                    counter_SS_dic[code]['first_neu'] += 1

                for code in SD_dic:
                    for key in SD_dic[code]:
                        if SS_dic[code][key] != 0:
                            SD_dic[code][key] = sqrt(SS_dic[code][key]/counter_SS_dic[code][key])

            for line in subject:
                subject_num = line[0]
                emotion = line[5]
                first_image_to_look = line[6]
                error = line[13]
                first_emo = line[14]
                first_neu = line[15]
                blink = line[16]
                code = first_image_to_look + emotion
                new_line = line
                for key in mean_dic[code]:
                    if key == 'first_emo':
                        score = first_emo
                    elif key == 'first_neu':
                        score = first_neu
                    if SD_dic[code][key] != None and score != "None" and "early" not in blink:
                        current_mean = mean_dic[code][key]
                        current_SD = SD_dic[code][key]
                        if (float(score) > (float(current_mean) + 3*float(current_SD)) or float(score) < (float(current_mean) - 3*float(current_SD))):
                                print(key, " in a ", emotion, " trial exceeds 3 SD for subject ", subject_num, " : ",
                                      str(score), ", mean: ", str(current_mean), ", SD: ", str(current_SD))
                                new_line.append("Deviant %s 3 SD" %key)
                        elif (float(score) > (float(current_mean) + 2*float(current_SD)) or float(score) < (float(current_mean) - 2*float(current_SD))):
                                print(key, " in a ", emotion, " trial exceeds 2 SD for subject ", subject_num, " : ",
                                      str(score), ", mean: ", str(current_mean), ", SD: ", str(current_SD))
                                new_line.append("Deviant %s 2 SD" %key)
                        else:
                            new_line.append("Normal %s value" %key)
                    else:
                        new_line.append("%s not relevant" %key)
                s = ";".join([str(e) for e in new_line]) + "\n"
                data_modified.write(s)
        data_modified.close()

    @staticmethod
    def getDefaultResultsFile():
        return joinPaths(getResultsFolder(), 'visual_selection.csv')

    @staticmethod
    def makeResultFile() -> None:
        createResultsFolder()
        Visual_selection.makeResultFile(getDefaultResultsFile)

    @staticmethod
    def makeResultFile(filename: str) -> None:
        f = open(filename, 'w')
        f.write(';'.join([
            'Subject',
            'Group',
            'TrialID',
            'Training',
            'Eye',
            'Emotion',
            'First image to look',
            'Emotion target',
            'Neutral target',
            'TargetSide',
            'Arrow orientation',
            'Position emo',
            'Position neu',
            'Errors',
            'First time on emotional target',
            'First time on neutral target',
            'Total fixation time on emotional target',
            'Total fixation time on neutral target',
            'First blink type',
            'First saccade'
        ]))
        f.write('\n')
        f.close()


    # Creates an image scanpath for one trial.
    def scanpath(self, subject_id, trial, frequency : int):
        plt.clf()

        frame_color = (0,0,0)
        emo_color = (1,0,0)
        target_color = (0,1,0)
        x_axis = self.eyetracker.screen_center[0] * 2
        y_axis = self.eyetracker.screen_center[1] * 2
        plt.axis([0, x_axis, 0, y_axis])
        plt.gca().invert_yaxis()
        plt.axis('off')

        # Plotting frames
        if trial.isTraining():
            plotRegion(self.eyetracker.left, frame_color)
            plotRegion(self.eyetracker.right, frame_color)
        else:
            if 'left' in trial.features['target_side']:
                plotRegion(self.eyetracker.left, emo_color)
                plotRegion(self.eyetracker.right, frame_color)
            elif 'right' in trial.features['target_side']:
                plotRegion(self.eyetracker.left, frame_color)
                plotRegion(self.eyetracker.right, emo_color)

        if 'left' in trial.features['arrow']:
            plotRegion(self.eyetracker.left_wide, target_color)
        elif 'right' in trial.features['arrow']:
            plotRegion(self.eyetracker.right_wide, target_color)

        # Plotting gaze positions
        trial.plot(frequency)
        if trial.isTraining():
            image_name = 'subject_%i_training_%i.png' % (subject_id, trial.getTrialId())
        else:
            image_name = 'subject_%i_trial_%i.png' % (subject_id, trial.getTrialId())
        saveImage(getTmpFolder(), image_name)
        return image_name

    # Creates a video scanpath for one trial.
    def scanpathVideo(self, subject_id, trial, frequency : int, progress = None):
        n_elem_drawn = 20
        point_list = trial.getGazePoints()
        nb_points = len(point_list)
        frame_color = (0,0,0)
        point_color = (1,1,0)
        target_color = (0,1,0)
        emo_color = (1,0,0)

        # Taking frequency into account
        point_list_f = []
        for i in range(0,len(point_list)-frequency,frequency):
            point_list_f.append(point_list[i])

        image_list = []

        axis_x = self.eyetracker.screen_center[0]*2
        axis_y = self.eyetracker.screen_center[1]*2

        logTrace ('Creating video frames', Precision.NORMAL)

        if progress != None:
            progress.setText(0, 'Loading frames')
            progress.setMaximum(0, len(point_list_f) - 1)

        for elem in range(0,len(point_list_f)-1):
            if progress != None:
                progress.increment(0)
            plt.clf()
            ax = plt.axis([0,axis_x,0,axis_y])
            plt.gca().invert_yaxis()
            plt.axis('off')

            for j in range(max(0,elem-n_elem_drawn),elem+1):
                plotSegment(point_list_f[j], point_list_f[j+1], c = point_color)
            point_color = (1, point_color[1] - 1.0/nb_points , 0)

            if trial.isTraining():
                plotRegion(self.eyetracker.left, frame_color)
                plotRegion(self.eyetracker.right, frame_color)
            else:
                if 'left' in trial.features['target_side']:
                    plotRegion(self.eyetracker.left, emo_color)
                    plotRegion(self.eyetracker.right, frame_color)
                elif 'right' in trial.features['target_side']:
                    plotRegion(self.eyetracker.left, frame_color)
                    plotRegion(self.eyetracker.right, emo_color)

            if 'left' in trial.features['arrow']:
                plotRegion(self.eyetracker.left_wide, target_color)
            elif 'right' in trial.features['arrow']:
                plotRegion(self.eyetracker.right_wide, target_color)

            image_name = '%i.png' % elem
            saveImage(getTmpFolder(), image_name)
            image_list.append(joinPaths(getTmpFolder(), image_name))
        if trial.isTraining():
            vid_name = 'subject_%i_training_%s.avi' % (subject_id, trial.getTrialId())
        else:
            vid_name = 'subject_%i_trial_%s.avi' % (subject_id, trial.getTrialId())
        progress.setText(0, 'Loading frames')
        makeVideo(image_list, vid_name, fps=100/frequency)
        return vid_name

    def getSubjectData(self, line: str) -> Union[Tuple[int,str]]:
        try:
            l = re.split("[\t ]+", line)
            return (int(l[1]), l[2])
        except:
            return None

    def processSubject(self, input_file : str, progress = None) -> Subject:

        self.selectEyetracker(input_file)

        with open(input_file) as f:
            first_line = f.readline()
            if first_line[-1] == '\n':
                first_line = first_line[:-1]

        subject_data = self.getSubjectData(first_line)

        if subject_data is None:
            raise ExperimentException('Subject number and category could not be found')

        else:
            result_file = "results.txt"
            is_processed = self.eyetracker.preprocess(input_file, result_file, progress)
            if is_processed:
                datafile = open(joinPaths(getTmpFolder(), result_file), "r")
            else:
                datafile = open(input_file, "r")

            #File conversion in list.
            data = datafile.read()
            data = list(data.splitlines())

            #We add a tabulation and space separator.
            data = [re.split("[\t ]+",line) for line in data]

            (n_subject, subject_cat) = subject_data
            return Subject(self, data, n_subject, subject_cat, progress)

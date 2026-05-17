import React, {useState} from 'react';
import {SafeAreaView, Text, TextInput, Pressable, Alert, View, StyleSheet} from 'react-native';
import {Suggestion, SuggestionWriteScreenProps} from '../types';

const MAX_TITLE_LENGTH = 50;
const MIN_CONTENT_LENGTH = 10;

type Props = SuggestionWriteScreenProps & {
  currentUser: string;
  addSuggestion: (suggestion: Suggestion) => Promise<boolean>;
};

export default function SuggestionWriteScreen({navigation, currentUser, addSuggestion}: Props) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitSuggestion = async () => {
    const trimmedTitle = title.trim();
    const trimmedContent = content.trim();

    if (!trimmedTitle) {
      Alert.alert('입력 오류', '제목을 입력해 주세요.');
      return;
    }
    if (!trimmedContent) {
      Alert.alert('입력 오류', '내용을 입력해 주세요.');
      return;
    }
    if (trimmedTitle.length > MAX_TITLE_LENGTH) {
      Alert.alert('입력 오류', `제목은 ${MAX_TITLE_LENGTH}자 이하로 입력해 주세요.`);
      return;
    }
    if (trimmedContent.length < MIN_CONTENT_LENGTH) {
      Alert.alert('입력 오류', `내용은 최소 ${MIN_CONTENT_LENGTH}자 이상 입력해 주세요.`);
      return;
    }

    setIsSubmitting(true);

    try {
      // 작성한 건의사항을 앱 내부 목록에 저장
      const suggestion: Suggestion = {
        id: `s-${Date.now()}`,
        title: trimmedTitle,
        content: trimmedContent,
        writer: currentUser,
        createdAt: new Date().toLocaleString('ko-KR'),
      };

      const saved = await addSuggestion(suggestion);
      if (!saved) {
        Alert.alert('저장 오류', '건의사항 저장 중 오류가 발생했습니다.');
        return;
      }

      Alert.alert('등록 완료', '건의사항이 등록되었습니다.');
      navigation.reset({index: 1, routes: [{name: 'ProductList'}, {name: 'Suggestions'}]});
    } catch {
      Alert.alert('저장 오류', '건의사항 저장 중 오류가 발생했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={localStyles.page}>
      <Text style={localStyles.subtitle}>원하는 상품, 이용 불편, 개선 의견을 자유롭게 적어주세요.</Text>

      <View style={localStyles.formCard}>
        <TextInput
          placeholder="제목을 입력하세요"
          placeholderTextColor="#94A3B8"
          value={title}
          onChangeText={setTitle}
          style={localStyles.input}
          editable={!isSubmitting}
        />
        <TextInput
          placeholder="건의사항 내용을 입력하세요"
          placeholderTextColor="#94A3B8"
          value={content}
          onChangeText={setContent}
          style={localStyles.contentInput}
          multiline
          editable={!isSubmitting}
        />
      </View>

      <Pressable
        style={[localStyles.submitBtn, isSubmitting && localStyles.submitBtnDisabled]}
        onPress={submitSuggestion}
        disabled={isSubmitting}>
        <Text style={localStyles.submitBtnText}>{isSubmitting ? '등록 중...' : '등록'}</Text>
      </Pressable>
    </SafeAreaView>
  );
}

const localStyles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    paddingHorizontal: 16,
    paddingTop: 10,
  },
  title: {
    color: '#111827',
    fontSize: 24,
    fontWeight: '800',
    marginBottom: 4,
  },
  subtitle: {
    color: '#64748B',
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  formCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    padding: 14,
    marginBottom: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 12,
    paddingVertical: 11,
    marginBottom: 10,
    fontSize: 15,
    color: '#111827',
  },
  contentInput: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 12,
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 12,
    paddingVertical: 11,
    minHeight: 140,
    fontSize: 15,
    color: '#111827',
    textAlignVertical: 'top',
  },
  submitBtn: {
    backgroundColor: '#0060AF',
    borderWidth: 1,
    borderColor: '#0060AF',
    paddingVertical: 13,
    borderRadius: 12,
    alignItems: 'center',
  },
  submitBtnDisabled: {
    backgroundColor: '#94A3B8',
    borderColor: '#94A3B8',
  },
  submitBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 15,
  },
});




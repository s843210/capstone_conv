import React from 'react';
import {SafeAreaView, Text, View, Pressable, Alert} from 'react-native';
import {SuggestionDetailScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

type Props = SuggestionDetailScreenProps & {
  currentUser: string;
  removeSuggestion: (suggestionId: string, currentUser: string) => Promise<boolean>;
};

export default function SuggestionDetailScreen({navigation, route, currentUser, removeSuggestion}: Props) {
  const {suggestion} = route.params;
  const isOwner = suggestion.writer === currentUser;

  const handleRemove = () => {
    Alert.alert('건의사항 삭제', '이 건의사항을 삭제하시겠습니까?', [
      {text: '취소', style: 'cancel'},
      {
        text: '삭제',
        style: 'destructive',
        onPress: async () => {
          const removed = await removeSuggestion(suggestion.id, currentUser);
          if (!removed) {
            Alert.alert('삭제 오류', '건의사항 삭제 중 오류가 발생했습니다.');
            return;
          }
          navigation.navigate('Suggestions');
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>{suggestion.title}</Text>
      <View style={styles.card}>
        <Text style={styles.cardMeta}>작성자: {suggestion.writer}</Text>
        <Text style={styles.cardMeta}>작성일: {suggestion.createdAt}</Text>
        {!!suggestion.updatedAt && <Text style={styles.cardMeta}>수정일: {suggestion.updatedAt}</Text>}
      </View>
      <View style={styles.card}>
        <Text style={styles.cardMeta}>{suggestion.content}</Text>
      </View>

      {isOwner && (
        <>
          <Pressable
            style={styles.secondaryBtn}
            onPress={() => navigation.navigate('SuggestionEdit', {suggestion})}>
            <Text style={styles.secondaryBtnText}>수정</Text>
          </Pressable>
          <Pressable style={styles.dangerGhostBtn} onPress={handleRemove}>
            <Text style={styles.dangerGhostBtnText}>삭제</Text>
          </Pressable>
        </>
      )}
    </SafeAreaView>
  );
}
